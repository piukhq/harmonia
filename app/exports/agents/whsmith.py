from app import models
from app.config import Config, ConfigValue, KEY_PREFIX
from app.exports.agents.bases.ecrebo import Ecrebo

PROVIDER_SLUG = "whsmith-rewards"

REWARD_UPLOAD_PATH_KEY = f"{KEY_PREFIX}{PROVIDER_SLUG}.reward_upload_path"
SCHEDULE_KEY = f"{KEY_PREFIX}{PROVIDER_SLUG}.schedule"


class WhSmith(Ecrebo):
    provider_slug = PROVIDER_SLUG
    matching_type = models.MatchingType.LOYALTY
    saved_output_index = 0  # No receipt file in outputs
    provider_short_code = "WHS"

    config = Config(
        ConfigValue("reward_upload_path", key=REWARD_UPLOAD_PATH_KEY, default="upload/staging/rewards"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )
