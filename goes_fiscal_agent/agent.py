# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Legal Analytics Agent"""

import logging
import yaml
from pathlib import Path

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from google.adk.tools import agent_tool

from . import tools
from .prompts import get_instructions
from .utils import get_env_var

from google.adk.code_executors import BuiltInCodeExecutor

# Env Variables
from dotenv import load_dotenv
load_dotenv()

# Load agent config
script_dir = Path(__file__).parent.absolute()
config_path = script_dir / 'config.yaml'

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)


def setup_before_agent_call(callback_context: CallbackContext) -> None:
    """Setup the agent."""
    pass


root_agent = Agent(
    model=get_env_var("AGENT_ROOT_MODEL"),
    name=config['agent_name'],
    instruction=get_instructions(),
    tools=[tools.get_bigquery_schema, tools.run_bigquery_query],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)