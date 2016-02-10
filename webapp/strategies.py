from __future__ import division
import datetime
from webapp import models
from flask.ext.security import current_user
from config import Constants


def rank_objects_for_product(product_id):
    now = datetime.datetime.utcnow()
    own_review = []
    featured_reviews = []
    regular_reviews = []
    star_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    star_rating_sum = 0
    reviews_with_stars = 0
    # Get all not deleted reviews
    all_reviews = models.Review.get_all_undeleted_reviews_for_product(product_id)
    for review in all_reviews:
        if review.star_rating:
            star_distribution[review.star_rating] += 1
            reviews_with_stars += 1
            star_rating_sum += review.star_rating
        review.rank_score = 0
        if review.user == current_user:
            own_review = [review]
        elif review.featured and review.featured.action == 1:
            featured_reviews.append(review)
        else:
            # Calculate days between now and the post of the review.
            days_since = (now - review.created_ts).days
            # Older reviews are penalized
            review.rank_score -= days_since * Constants.REVIEW_RANK_DAYS_WEIGHT
            if review.user:
                # Promote liked users
                review.rank_score += review.user.likes_count * Constants.REVIEW_RANK_USER_LIKES_WEIGHT
                # Promote users with more reviews
                review.rank_score += review.user.reviews_count * Constants.REVIEW_RANK_USER_REVIEWS_WEIGHT
            # Promote reviews with more likes
            review.rank_score += review.likes * Constants.REVIEW_RANK_LIKES_WEIGHT
            # Promote verified reviews
            review.rank_score += Constants.REVIEW_RANK_IS_VERIFIED_WEIGHT if review.verified_review else 0
            # Penalize reviews with more reports
            review.rank_score -= review.reports * Constants.REVIEW_RANK_REPORTS_WEIGHT
            # Promote reviews with images
            review.rank_score += Constants.REVIEW_RANK_HAS_IMAGE_WEIGHT if review.image_url else 0
            # Promote reviews with videos
            review.rank_score += Constants.REVIEW_RANK_HAS_VIDEO_WEIGHT if review.youtube_video else 0
            # TODO: Promote by number of shares
            # Add it to regular reviews
            regular_reviews.append(review)
    # Sort by rank_score
    regular_reviews = sorted(regular_reviews, key=lambda x: x.rank_score, reverse=True)
    final_rank = own_review + featured_reviews + regular_reviews
    # calculate average stars:
    total_reviews = len(final_rank)
    average_stars = star_rating_sum / reviews_with_stars if reviews_with_stars else 0
    return {
        'total_reviews': total_reviews,
        'objs_list': final_rank,
        'average_stars': average_stars,
        'main_star_distribution': star_distribution
    }
