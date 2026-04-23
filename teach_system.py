from database_utilities import get_actions, insert_trigger_word
from load_operations import load_operations


def teach_trigger_word(word, action_name):
    success, message = insert_trigger_word(word, action_name)
    if success:
        load_operations()
    return message


def handle_teach(user_input):
    parts = user_input.strip().split()

    if len(parts) < 3:
        return "Use: teach <trigger word> <action>"

    words = parts[1:]
    actions = get_actions()

    for action_name, symbol in actions:
        action_parts = action_name.lower().split()
        if [part.lower() for part in words[-len(action_parts):]] == action_parts:
            word = " ".join(words[:-len(action_parts)]).strip()
            if not word:
                return "Use: teach <trigger word> <action>"
            return teach_trigger_word(word, action_name)

        if words[-1] == symbol:
            word = " ".join(words[:-1]).strip()
            if not word:
                return "Use: teach <trigger word> <action>"
            return teach_trigger_word(word, action_name)

    word = parts[1]
    action_name = " ".join(parts[2:])
    return teach_trigger_word(word, action_name)
