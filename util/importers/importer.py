from webapp.models import User, UserLegacy


class OpinewImporter(object):

    """
    creates a new user if his email doesn't match in the db
    """
    @classmethod
    def create_or_match_user_from_review_data(cls, reviewer_name, email):
        user = None
        existing_user = User.get_by_email_no_exception(email)
        if existing_user:
            user = existing_user
        else:
            user, is_new = UserLegacy.get_or_create_by_email(email, name=reviewer_name)

        return user
