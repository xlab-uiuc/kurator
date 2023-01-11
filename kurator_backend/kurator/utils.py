import difflib
import os
import subprocess
import pandas as pd
import openai
import yaml
from manifest import Manifest
from fastcore.basics import *
from fastcore.meta import delegates
from starlette.config import Config

from pathlib import Path
from typing import *

SRC_PATH = Path(__file__).parent
ROOT_PATH = SRC_PATH.parent

df_crd_info = pd.read_csv(ROOT_PATH / "crd_info.csv")


###### Model ######

def load_gpt3_creds():
    config = Config()
    openai.api_key = config.environ['OPENAI_API_KEY']

class Model():
    def __init__(
        self,
        model_provider: str,
        model_name: str,
        n: int = 1,
        temperature: float = 0.3,
        top_p = 1,
        max_tokens = 250,
        stop = ["```"],
        use_cache = True,
    ):
        store_attr()

        supported_providers = ["openai"]
        assert model_provider in supported_providers, f"model_provider must be one of {supported_providers}"

        args = dict(
            client_name = model_provider,
        )
        if use_cache:
            args["cache_name"] = "sqlite"
            args["cache_connection"] = ROOT_PATH/"manifest_cache.db"

        if model_provider == "openai":
            load_gpt3_creds()
            args["client_connection"] = openai.api_key
            args["engine"] = model_name
            args["n"] = n
            args["top_k_return"] = n
            args["temperature"] = temperature
            args["top_p"] = top_p
            args["max_tokens"] = max_tokens
            args["stop_sequence"] = stop

        self.M = Manifest(**args)
        self.rate_limit = 150000

    @delegates(Manifest.run)
    def query(self, prompt: str, debug: bool=False, **kwargs) -> List[str]:
        if "n" in kwargs and "top_k_return" not in kwargs and self.model_provider == "openai":
            kwargs["top_k_return"] = kwargs["n"]

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        orig_n = n = kwargs.get("n", self.n)
        rate = max_tokens * n

        while rate > self.rate_limit:
            if debug: print(f"Rate limit exceeded. Reducing n from {n} to {n//2}")
            n = n // 2
            rate = max_tokens * n
        assert n > 0, "n is too small to fit within rate limit"

        results = []
        tries_left = 5
        while len(results) < orig_n and tries_left > 0:
            kwargs["n"] = n
            try:
                result = self.M.run(prompt, **kwargs)
                if isinstance(result, str):
                    results.append(result)
                else:
                    results.extend(result)
            except Exception as e:
                print(e)
                tries_left -= 1
                n = max(n // 2, 1)
                continue

        return results

CodexModel = Model("openai", "code-davinci-002")

###### Validation ######

def get_crd_info_row(crd_api_version: str, crd_name: str):
    crd_info_rows = df_crd_info[
        (df_crd_info.crd_name == crd_name) &
        (df_crd_info.api_version == crd_api_version)
    ].to_dict(orient='records')
    # pick the one with latest version
    def key_fn(row):
        v = row['version'].split('-')[0]
        return tuple(map(int, v.split('.')))
    crd_info_row = sorted(crd_info_rows, key=key_fn, reverse=True)[0]
    return crd_info_row

def get_json_schema_file_name_for_crd(crd_api_version: str, crd_name: str) -> Path:
    crd_info_row = get_crd_info_row(crd_api_version, crd_name)
    crd_operator = crd_info_row['operator']
    crd_kind = crd_info_row['crd_name']
    operator_version = crd_info_row['version']
    crd_api_version = crd_info_row['api_version'].split("/")[1]

    crd_schemas_path = ROOT_PATH / "crd_schemas"
    return crd_schemas_path / f"{crd_operator}/{operator_version}/{crd_kind.lower()}_{crd_api_version}.json"


def unzip_community_operators_if_needed():
    community_operators_path = ROOT_PATH / "community-operators"
    if community_operators_path.exists():
        return

    community_operators_zip_path = ROOT_PATH / "community-operators.zip"
    assert community_operators_zip_path.exists(), "community-operators.zip does not exist. Check if installation was proper."

    subprocess.run(["unzip", "-o", community_operators_zip_path, "-d", ROOT_PATH], check=True)

def validate_single_doc(
    config_doc: dict, ignore_schema_not_found: bool = False, k8s_version: str = "master"
) -> Optional[str]:
    if len(config_doc) == 0:
        # empty config is valid
        return ""

    if "kind" not in config_doc:
        return "No `kind` specified"
    crd_kind = config_doc['kind']

    if "apiVersion" not in config_doc:
        return "No `apiVersion` specified"
    crd_api_version = config_doc['apiVersion']

    assume_inbuilt = False
    crd_json_path = None
    try:
        crd_json_path = get_json_schema_file_name_for_crd(crd_api_version, crd_kind)
    except Exception as e:
        assume_inbuilt = True

    if crd_json_path and not crd_json_path.exists():
        crd_json_path.parent.mkdir(parents=True, exist_ok=True)
        # run openapi2jsonschema to generate the schema
        crd_info_row = get_crd_info_row(crd_api_version, crd_kind)
        crd_yaml_path = crd_info_row['crd_path']
        crd_yaml_path = ROOT_PATH / crd_yaml_path
        if not crd_yaml_path.exists():
            # check if community-operators is already extracted
            unzip_community_operators_if_needed()
            assert crd_yaml_path.exists(), f"CRD yaml path {crd_yaml_path} does not exist"

        env = os.environ.copy()
        env["FILENAME_FORMAT"] = "{kind}_{version}"
        result = subprocess.run(
            ["python3", str(SRC_PATH/"openapi2jsonschema.py"), str(crd_yaml_path)], cwd=str(crd_json_path.parent), env=env,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(result.stderr)
            return "Failed to generate schema for CRD"
        assert crd_json_path.exists(), f"Schema file not generated: {crd_json_path}"

    # run kubeconfirm to validate the config
    if assume_inbuilt:
        cache_path = ROOT_PATH/"crd_schemas/inbuilt_crd_cache"
        cache_path.mkdir(parents=True, exist_ok=True)
        cmd = [str((ROOT_PATH/"kubeconform").absolute()), "-strict", "-cache", str(cache_path)]
    else:
        cmd = [str((ROOT_PATH/"kubeconform").absolute()), "-strict", "-schema-location", str(crd_json_path)]
    cmd += ["-kubernetes-version", k8s_version]
    # print(" ".join(cmd))
    validation_result = subprocess.run(
        cmd,
        input=yaml.dump(config_doc).encode('utf-8'),
        capture_output=True,
    )
    if validation_result.returncode != 0:
        error = validation_result.stdout.decode('utf-8')
        print(f"Command `{' '.join(cmd)}` failed with error: {error}")
        if error.startswith("stdin - "):
            error = error[len("stdin - "):]
        if "Could not find schema for" in error and ignore_schema_not_found:
            return None
        return error
    return None


def validate_config(config_s: str) -> Optional[str]:
    # validate that the config is valid
    try:
        configs = list(yaml.load_all(config_s, Loader=yaml.SafeLoader))
    except Exception as e:
        return "Invalid YAML?"

    for config_doc in configs:
        if config_doc is None:
            continue
        error = validate_single_doc(config_doc)
        if error is not None:
            return error
    return None

###### Misc ######

def get_diff(a: str, b: str) -> str:
    diff = difflib.ndiff(a.splitlines(), b.splitlines())
    return "\n".join(diff)
