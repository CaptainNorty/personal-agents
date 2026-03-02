# Import all models so they register with Base.metadata before create_all()
from app.bots.nutrition.models import DailySummary, FoodItemCache, FoodLog  # noqa: F401
from app.bots.podcast.models import PodcastEpisode  # noqa: F401
from app.bots.social.models import SocialEntry  # noqa: F401
