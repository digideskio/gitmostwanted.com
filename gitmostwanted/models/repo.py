from sqlalchemy.dialects.mysql import TINYINT, SMALLINT
from sqlalchemy.sql import expression
from gitmostwanted.lib.status import Status
from gitmostwanted.lib.regex import SearchTerm
from gitmostwanted.lib.text import TextWithoutSmilies
from gitmostwanted.lib.url import Url
from gitmostwanted.app import db
from werkzeug.datastructures import ImmutableMultiDict
from datetime import datetime


class Repo(db.Model):
    __tablename__ = 'repos'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8',
        'mysql_collate': 'utf8_general_ci'
    }

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    language = db.Column(db.String(25))
    full_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(250))
    html_url = db.Column(db.String(150), nullable=False)
    homepage = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, nullable=False, index=True)
    checked_at = db.Column(db.DateTime, index=True)
    mature = db.Column(db.Boolean, nullable=False, server_default=expression.false(), index=True)
    worth = db.Column(TINYINT(display_width=2), nullable=False, server_default='3', index=True)
    stargazers_count = db.Column(db.Integer, nullable=False, server_default='0')
    status_updated_at = db.Column(db.DateTime)
    status = db.Column(
        db.Enum('promising', 'new', 'unknown', 'deleted', 'hopeless'),
        server_default='new', nullable=False, index=True
    )

    def __setattr__(self, key, value):
        if key == 'status' and self.status != value:
            value = str(Status(value))
            self.status_updated_at = datetime.now()

        if key == 'homepage':
            value = str(Url(value)) if value else None

        if key == 'description':
            value = str(TextWithoutSmilies(value[:250])) if value else None

        super().__setattr__(key, value)

    @classmethod
    def filter_by_args(cls, q, args: ImmutableMultiDict):
        lang = args.get('lang')
        if lang != 'All' and (lang,) in cls.language_distinct():
            q = q.filter(cls.language == lang)

        status = args.get('status')
        if status in ('promising', 'hopeless'):
            q = q.filter(cls.status == status)

        if bool(args.get('mature')):
            q = q.filter(cls.mature.is_(True))

        try:
            q = q.filter(cls.full_name.like(str(SearchTerm(args.get('term', '')))))
        except ValueError:
            pass

        return q

    @staticmethod
    def language_distinct():
        if not hasattr(Repo.language_distinct, 'memoize'):
            q = db.session.query(Repo.language).distinct().filter(Repo.language.isnot(None))
            setattr(Repo.language_distinct, 'memoize', sorted(q.all()))
        return getattr(Repo.language_distinct, 'memoize')

    @classmethod
    def get_one_by_full_name(cls, name):
        return cls.query.filter(cls.full_name == name).first()


class RepoStars(db.Model):
    __tablename__ = 'repos_stars'

    repo_id = db.Column(
        db.BigInteger, db.ForeignKey('repos.id', name='fk_repos_stars_repo_id', ondelete='CASCADE'),
        primary_key=True
    )
    stars = db.Column(
        SMALLINT(display_width=4, unsigned=True),
        nullable=False
    )
    year = db.Column(
        SMALLINT(display_width=4, unsigned=True),
        autoincrement=False, nullable=False, primary_key=True
    )
    day = db.Column(
        SMALLINT(display_width=3, unsigned=True),
        autoincrement=False, nullable=False, primary_key=True
    )


class RepoMean(db.Model):
    __tablename__ = 'repos_mean'

    repo = db.relationship(Repo)
    repo_id = db.Column(
        db.BigInteger, db.ForeignKey('repos.id', name='fk_repos_mean_repo_id', ondelete='CASCADE'),
        primary_key=True
    )
    created_at = db.Column(
        db.Date,
        default=datetime.today().strftime('%Y-%m-%d'), nullable=False, primary_key=True
    )
    value = db.Column(db.Float(), nullable=False)
