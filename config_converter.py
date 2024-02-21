from collections import defaultdict
import yaml
import os.path
from pathlib import Path

CONFIG_MAPPING = {
    "Discord.Token": "Secrets.Discord.Token",
    "Discord.StreamChannel": "Discord.Channels.Stream",
    "Discord.WelcomeChannel": "Discord.Channels.Welcome",
    "Discord.PendingRewardChannel": "Discord.ChannelPoints.PendingRewardChannel",
    "Discord.PointsAuditChannel": "Discord.ChannelPoints.PointsAuditChannel",
    "Discord.Tier1RoleID": "Discord.Subscribers.Tier1Role",
    "Discord.Tier2RoleID": "Discord.Subscribers.Tier2Role",
    "Discord.Tier3RoleID": "Discord.Subscribers.Tier3Role",
    "Discord.GiftedTier1RoleID": "Discord.Subscribers.GiftedTier1Role",
    "Discord.GiftedTier2RoleID": "Discord.Subscribers.GiftedTier2Role",
    "Discord.GiftedTier3RoleID": "Discord.Subscribers.GiftedTier3Role",
    "Discord.GuildID": "Discord.GuildID",
    "Discord.VODApprovedRoleID": "Discord.VODReview.ApprovedRole",
    "Discord.VODSubmissionChannelID": "Discord.VODReview.SubmissionChannel",
    "Discord.GoodMorningRewardRequirement": "Discord.GoodMorning.RewardRequirement",
    "Discord.GoodMorningRewardRoleID": "Discord.GoodMorning.RewardRole",
    "Discord.GoodMorningRewardRedemptionChannelID": (
        "Discord.GoodMorning.RedemptionChannel"
    ),
    "Discord.CrowdMuteEmojiID": "Discord.CrowdMute.Emoji",
    "Discord.CrowdMuteThreshold": "Discord.CrowdMute.Threshold",
    "Discord.CrowdMuteDuration": "Discord.CrowdMute.Duration",
    "Discord.CoolEmojiID": "Discord.CoolMeter.CoolEmoji",
    "Discord.UncoolEmojiID": "Discord.CoolMeter.UncoolEmoji",
    "Discord.6MonthTier3RoleID": "Discord.Subscribers.6MonthTier3Role",
    "Discord.TwitchTier3RoleID": "Discord.Subscribers.TwitchTier3Role",
    "Discord.NAOpenInhouseChannel": "Discord.Inhouses.NAOpenChannel",
    "Discord.EUOpenInhouseChannel": "Discord.Inhouses.EUOpenChannel",
    "Discord.BotRoleID": "Discord.Roles.Bot",
    "Discord.ModRoleID": "Discord.Roles.Mod",
    "Predictions.PredictionChannelID": "Discord.Predictions.Channel",
    "TempRoles.ExpirationCheckCadenceMinutes": (
        "Discord.TempRoles.ExpirationCheckCadenceMinutes"
    ),
    "VODApproval.ApprovedTag": "Discord.VODReview.ApprovedTag",
    "VODApproval.RejectedTag": "Discord.VODReview.RejectedTag",
    "VODApproval.ApprovedRole": "Discord.VODReview.ApprovedRole",
    "VODApproval.RejectedRole": "Discord.VODReview.RejectedRole",
    "VODApproval.HoursPerReview": "Discord.VODReview.RewardHoursPerReview",
    "Server.AuthToken": "Secrets.Server.Token",
    "MySQL.Username": "Database.Username",
    "MySQL.Password": "Secrets.Database.Password",
    "MySQL.Host": "Database.Host",
    "MySQL.Name": "Database.Name",
}

STRING_VALUES = set(
    [
        "Database.Username",
        "Database.Host",
        "Database.Name",
        "Secrets.Discord.Token",
        "Secrets.Server.Token",
        "Secrets.Database.Password",
    ]
)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.yaml")
SECRETS_FILE = os.path.join(os.path.dirname(__file__), "secrets.yaml")


def read_config_value(key: str, config: defaultdict):
    key_split = key.split(".")
    curr_val = config
    for key_part in key_split:
        curr_val = curr_val[key_part]
    return curr_val


def write_config_value(key: str, value: any, config: defaultdict):
    key_split = key.split(".")
    curr_dict = config
    for key_part in key_split[:-1]:
        curr_dict = curr_dict[key_part]
    if key not in STRING_VALUES:
        value = int(value)
    curr_dict[key_split[-1]] = value


def recursive_defaultdict():
    return defaultdict(recursive_defaultdict)


def defaultdict_to_regular(d):
    if isinstance(d, defaultdict):
        d = {k: defaultdict_to_regular(v) for k, v in d.items()}
    return d


def main():
    # This is absurdly janky and never belongs in
    # real production code. Since this is a utility
    # script, we accept the jank.
    # Prevent FileNotFound exception so that we can
    # use the existing config.ini to write our new
    # config.yaml + secrets.yaml
    Path(CONFIG_FILE).touch()
    Path(SECRETS_FILE).touch()
    from config import Config

    new_config = defaultdict(recursive_defaultdict)
    for mapping_key, mapping_value in CONFIG_MAPPING.items():
        value = read_config_value(mapping_key, Config.CONFIG)
        write_config_value(mapping_value, value, new_config)
    new_config = defaultdict_to_regular(new_config)
    secrets = new_config["Secrets"]
    del new_config["Secrets"]
    result = yaml.safe_dump(new_config)

    with open(SECRETS_FILE, "w") as secrets_file:
        yaml.safe_dump(secrets, secrets_file)

    with open(CONFIG_FILE, "w") as config_file:
        yaml.safe_dump(new_config, config_file)


if __name__ == "__main__":
    main()
