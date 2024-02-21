import json
from os import listdir
from urllib.parse import urlparse

TEXT_FIELDS = set(
    [
        "headerLeft",
        "headerRight",
        "sideBannerTextOne",
        "sideBannerTextTwo",
        "sideBannerTextThree",
    ]
)

MEDIA_FIELDS = set(["backgroundVideo", "preRollVideo", "headerIcon", "sideBannerIcon"])


def convert_to_text(value: str):
    return {"type": "text", "value": value}


def convert_to_media(source: str):
    return {"type": "media", "source": source}


def convert_timer(duration: int | None):
    if duration is None:
        return None
    return {"duration": duration}


def convert_title(value: str):
    try:
        result = urlparse(value)
        if all([result.scheme, result.netloc]):
            return convert_to_media(value)
        return convert_to_text(value)
    except:
        return convert_to_text(value)


def stay_same(value: any):
    return value


CONVERSION_MAPPING = {
    "title": convert_title,
    "timer": convert_timer,
    "display": stay_same,
    "scrollingText": stay_same,
    "headerLeft": convert_to_text,
    "headerRight": convert_to_text,
    "sideBannerTextOne": convert_to_text,
    "sideBannerTextTwo": convert_to_text,
    "sideBannerTextThree": convert_to_text,
    "backgroundVideo": convert_to_media,
    "preRollVideo": convert_to_media,
    "headerIcon": convert_to_media,
    "sideBannerIcon": convert_to_media,
}


def main():
    new_contents = {}
    input_files = listdir("./old_requests")
    for input_file in input_files:
        with open(f"./old_requests/{input_file}", "r") as f:
            original_contents: dict = json.loads(f.read())
            for key, value in original_contents.items():
                new_contents[key] = CONVERSION_MAPPING[key](value)

        with open(f"./new_requests/{input_file}", "w") as f:
            f.write(json.dumps(new_contents, indent=2))


if __name__ == "__main__":
    main()
