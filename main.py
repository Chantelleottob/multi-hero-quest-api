from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Notion API configuration
NOTION_TOKEN = "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"
QUESTS_DATABASE_ID = "1e4e98df78c0801bb998e33020586d3d"

from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Notion API configuration - UPDATE THESE WITH YOUR ACTUAL VALUES
NOTION_TOKEN = "your_notion_integration_token"  # Replace with your actual token
QUESTS_DATABASE_ID = "your_quests_database_id"  # Replace with your actual database ID

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def parse_hero_substat(hero_substats_string):  # Fixed function name
    """
    Parse 'Creativity - Chantelle, Rizzma - Bob, Logic - Rudy' 
    into {'Chantelle': 'Creativity', 'Bob': 'Rizzma', 'Rudy': 'Logic'}
    """
    hero_substat_map = {}
    pairs = hero_substat_string.split(',')  # Fixed variable name

    for pair in pairs:
        pair = pair.strip()
        if ' - ' in pair:
            substat, hero = pair.split(' - ', 1)
            hero_substat_map[hero.strip()] = substat.strip()

    return hero_substat_map


def create_notion_quest(quest_data):
    """Create a new quest record in Notion"""
    url = f"https://api.notion.com/v1/pages"

    # Build the properties based on your Notion database structure
    properties = {
        "Quest Name": {
            "title": [{
                "text": {
                    "content": quest_data["quest_name"]
                }
            }]
        },
        "Hero Name": {
            "multi_select": [{
                "name": quest_data["hero_name"]
            }]
        },
        "Hero Substat": {
            "rich_text": [{
                "text": {
                    "content": quest_data["hero_substat"]
                }
            }]
        },
        "Difficulty": {
            "select": {
                "name": quest_data["difficulty"]
            }
        },
        "XP Value": {
            "number": quest_data["xp_value"]
        },
        "Multi Hero Quest": {
            "checkbox": False  # Individual quests are not multi-hero
        }
    }

    payload = {
        "parent": {
            "database_id": QUESTS_DATABASE_ID
        },
        "properties": properties
    }

    response = requests.post(url,
                             headers=NOTION_HEADERS,
                             data=json.dumps(payload))
    return response


@app.route('/webhook/notion', methods=['POST'])
def handle_notion_webhook():
    """Handle webhook from Notion when a multi-hero quest is created"""
    try:
        data = request.json

        # Extract quest data from Notion webhook
        properties = data.get('properties', {})

        # Check if this is a multi-hero quest
        multi_hero = properties.get('Multi Hero Quest',
                                    {}).get('checkbox', False)
        if not multi_hero:
            return jsonify({"message":
                            "Not a multi-hero quest, skipping"}), 200

        # Extract quest details
        quest_name = properties.get('Quest Name', {}).get(
            'title', [{}])[0].get('text', {}).get('content', '')

        # Handle hero names from multi-select
        hero_names_data = properties.get('Hero Name',
                                         {}).get('multi_select', [])
        hero_names = [hero.get('name', '') for hero in hero_names_data]

        hero_substat = properties.get('Hero Substat', {}).get(
            'rich_text', [{}])[0].get('text', {}).get('content', '')
        difficulty = properties.get('Difficulty', {}).get('select',
                                                          {}).get('name', '')
        xp_value = properties.get('XP Value', {}).get('number', 0)

        # Process the multi-hero quest
        result = process_multi_hero_quest(quest_name, hero_names, hero_substat,
                                          difficulty, xp_value)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/process-quest', methods=['POST'])
def process_multi_hero_quest_endpoint():
    """Direct API endpoint to process multi-hero quests"""
    try:
        data = request.json

        quest_name = data.get('quest_name')
        hero_names = data.get('hero_names')  # List of hero names
        hero_substat = data.get(
            'hero_substat'
        )  # String like "Creativity - Chantelle, Rizzma - Bob"
        difficulty = data.get('difficulty')
        xp_value = data.get('xp_value')

        result = process_multi_hero_quest(quest_name, hero_names, hero_substat,
                                          difficulty, xp_value)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def process_multi_hero_quest(quest_name, hero_names, hero_substats, difficulty,
                             xp_value):
    """Core function to break down multi-hero quest into individual quests"""

    # Parse hero substats mapping - Fixed function name
    hero_substat_map = parse_hero_substat(hero_substats)

    created_quests = []
    errors = []

    # Create individual quest for each hero
    for hero_name in hero_names:
        hero_name = hero_name.strip()

        # Get this hero's substat
        hero_substat = hero_substat_map.get(hero_name)
        if not hero_substat:
            errors.append(f"No substat found for hero: {hero_name}")
            continue

        # Format the hero substat with hero name
        formatted_substat = f"{hero_substat} - {hero_name}"

        # Create individual quest data
        individual_quest = {
            "quest_name": quest_name,
            "hero_name": hero_name,
            "hero_substat": formatted_substat,
            "difficulty": difficulty,
            "xp_value": xp_value
        }

        # Create the quest in Notion
        response = create_notion_quest(individual_quest)

        if response.status_code == 200:
            created_quests.append({
                "hero": hero_name,
                "status": "created",
                "quest_data": individual_quest
            })
        else:
            errors.append({
                "hero": hero_name,
                "error": f"Failed to create quest: {response.text}"
            })

    return {
        "message": f"Processed {len(created_quests)} individual quests",
        "created_quests": created_quests,
        "errors": errors
    }


@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify API is working"""
    return jsonify({
        "message": "Multi-Hero Quest API is running",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/')
def home():
    return jsonify({
        "message": "Multi-Hero Quest API",
        "endpoints": {
            "test": "/test",
            "process_quest": "/process-quest"
        }
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
