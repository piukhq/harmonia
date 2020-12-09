from app import config, models
from app.exports.agents.bases.ecrebo import Ecrebo, EcreboConfig

PROVIDER_SLUG = "whsmith-rewards"

REWARD_UPLOAD_PATH_KEY = f"{config.KEY_PREFIX}{PROVIDER_SLUG}.reward_upload_path"
SCHEDULE_KEY = f"{config.KEY_PREFIX}{PROVIDER_SLUG}.schedule"


class WhSmith(Ecrebo):
    provider_slug = PROVIDER_SLUG
    matching_type = models.MatchingType.LOYALTY
    saved_output_index = 0  # No receipt file in outputs
    provider_short_code = "WHS"

    class Config(EcreboConfig):
        reward_upload_path = config.ConfigValue(REWARD_UPLOAD_PATH_KEY, default="upload/staging/rewards")
        schedule = config.ConfigValue(SCHEDULE_KEY, "* * * * *")
