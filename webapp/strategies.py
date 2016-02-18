from __future__ import division
import datetime
from webapp import models
from flask import url_for
from flask.ext.security import current_user
from config import Constants


def calculate_regular_review_score(review, timestamp):
    # Calculate days between now and the post of the review.
    days_since = (timestamp - review.created_ts).days
    # Older reviews are penalized
    review.rank_score -= days_since * Constants.REVIEW_RANK_DAYS_WEIGHT
    if review.user:
        # Promote liked users
        review.rank_score += len(review.user.reviews) * Constants.REVIEW_RANK_USER_LIKES_WEIGHT
        # Promote users with more reviews
        review.rank_score += len(review.user.review_likes) * Constants.REVIEW_RANK_USER_REVIEWS_WEIGHT
    # Promote reviews with more likes
    review.rank_score += len(review.likes) * Constants.REVIEW_RANK_LIKES_WEIGHT
    # Promote reviews with more shares
    review.rank_score += len(review.shares) * Constants.REVIEW_RANK_SHARES_WEIGHT
    # Promote reviews with more comments
    review.rank_score += len(review.comments) * Constants.REVIEW_RANK_COMMENTS_WEIGHT
    # Penalize reviews with more reports
    review.rank_score -= len(review.reports) * Constants.REVIEW_RANK_REPORTS_WEIGHT
    # Promote verified reviews
    review.rank_score += Constants.REVIEW_RANK_IS_VERIFIED_WEIGHT if review.verified_review else 0
    # Promote reviews with images
    review.rank_score += Constants.REVIEW_RANK_HAS_IMAGE_WEIGHT if review.image_url else 0
    # Promote reviews with videos
    review.rank_score += Constants.REVIEW_RANK_HAS_VIDEO_WEIGHT if review.youtube_video else 0


def calculate_question_score(question, timestamp):
    # Calculate days between now and the post of the review.
    days_since = (timestamp - question.created_ts).days
    # Older reviews are penalized
    question.rank_score -= days_since * Constants.QUESTION_RANK_DAYS_WEIGHT


def rank_objects_for_product(product_id):
    now = datetime.datetime.utcnow()
    own_review = []
    featured_reviews = []
    regular_reviews = []
    questions = []
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
        elif review.featured:
            featured_reviews.append(review)
        else:
            calculate_regular_review_score(review, timestamp=now)
            # Add it to regular reviews
            regular_reviews.append(review)

    # Get all questions
    all_questions = models.Question.get_all_questions_for_product(product_id)
    for question in all_questions:
        question.rank_score = 0
        calculate_question_score(question, timestamp=now)
        # Add it to list of questions
        questions.append(question)

    # Merge questions and regular reviews
    question_review_rank = questions + regular_reviews

    # Sort by rank_score
    question_review_rank = sorted(question_review_rank, key=lambda x: x.rank_score, reverse=True)
    final_rank = own_review + featured_reviews + question_review_rank

    # calculate average stars:
    total_reviews = len(own_review + featured_reviews + regular_reviews)
    average_stars = star_rating_sum / reviews_with_stars if reviews_with_stars else 0

    return {
        'total_reviews': total_reviews,
        'objs_list': final_rank,
        'average_stars': average_stars,
        'main_star_distribution': star_distribution
    }

def get_incoming_messages(shop):
    return [
        {
            'url': url_for('client.setup_plugin'),
            'icon': 'copy',
            'icon_bg_color': Constants.COLOR_OPINEW_KIWI,
            'title': 'Set up plugin on your shop'
        },
        {
            'url': "javascript:showTab('#account');",
            'icon': 'briefcase',
            'icon_bg_color': Constants.COLOR_OPINEW_AQUA,
            'title': 'Set up billing'
        },
        {
            'url': url_for('security.change_password'),
            'icon': 'pencil',
            'icon_bg_color': Constants.COLOR_OPINEW_AQUA,
            'title': 'Change your password'
        }
    ]

def get_scheduled_tasks(shop):
    scheduled_tasks = []
    for order in shop.orders:
        for task in order.tasks:
            if task.status == "PENDING":
                obj = {
                    'title': task.method,
                    'icon': 'envelope',
                    'eta': task.eta,
                    'user': order.user,
                    'products': order.products
                }
                scheduled_tasks.append(obj)
    return sorted(scheduled_tasks, key=lambda x: x['eta'])