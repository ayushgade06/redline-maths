"""List the Claude models this API key can use (milestone 4: verify the model id).

python scripts/list_models.py
"""

from dotenv import load_dotenv

load_dotenv()

import anthropic  # noqa: E402

for m in anthropic.Anthropic().models.list():
    print(m.id, "|", m.display_name)
