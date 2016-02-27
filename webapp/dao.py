from webapp import db, models


class DAO(object):
    def flush(self):
        pass


class DAO_SA(DAO):
    def flush(self):
        db.session.commit()


class ReviewDAO(object):
    @classmethod
    def create(cls):
        pass


class ReviewDAO_SA(ReviewDAO, DAO_SA):
    model = models.Review

    @classmethod
    def create(cls, **kwargs):
        instance = cls.model(**kwargs)
        db.session.add(instance)
        return instance

# Factory for DAOs
dao = DAO_SA()
review_dao = ReviewDAO_SA

# Example use
review = review_dao.create(body='Hello world')
dao.flush()