"""`mise run models:fetch`: download the configured Whisper model into the Hugging Face cache."""

from huggingface_hub import snapshot_download  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]

from stremio_plus_plus.config.env import load_env
from stremio_plus_plus.config.settings_file import SettingsFile


def main() -> None:
    model = SettingsFile(load_env().config_dir).settings.subtitles.speech.model
    print(snapshot_download(model))  # noqa: T201  # the CLI's output


if __name__ == "__main__":
    main()
