# -*- coding: utf-8 -*-
from typing import List


def create_instruct(
        target: List[str], 
        simulated_profile: dict, 
        simulated_personality: dict, 
        assistant_name: str, 
        domain_knowledge: List[List], 
        seed_conversation: dict
    ):
    """Create instructions about the conversation environment and roles."""
    domain = ""
    target_action = target[0].lower()
    if "movie" in target_action:
        domain = "movie"
    elif "music" in target_action:
        domain = "music"
    elif "food" in target_action:
        domain = "food"
    elif "poi" in target_action:
        domain = "poi"
    else:
        raise ValueError("Invalid target action: {}".format(target_action))
    
    # Describe the environment (shared by all roles)
    if domain == "movie" or domain == "music":
        env_desc = "You are participating in a conversation about music or movies."
    else:
        env_desc = "You are participating in a conversation about delicious food or point-of-interest (POI)."
    
    # Describe the user
    user_desc = "You are {}, ".format(simulated_profile["Name"])
    profile_desc = ""
    
    if simulated_profile["Occupation"] == "Student":
        if simulated_profile["Gender"] == "Male":
            profile_desc = "a male student in the age range of {}, living in {}".format(simulated_profile["Age Range"].lower(), simulated_profile["Residence"])
        else:
            profile_desc = "a female student in the age range of {}, living in {}".format(simulated_profile["Age Range"].lower(), simulated_profile["Residence"])
    elif simulated_profile["Occupation"] == "Employed":
        if simulated_profile["Gender"] == "Male":
            profile_desc = "a man in the age range of {}, working in a company and living in {}".format(simulated_profile["Age Range"].lower(), simulated_profile["Residence"])
        else:
            profile_desc = "a woman in the age range of {}, working in a company and living in {}".format(simulated_profile["Age Range"].lower(), simulated_profile["Residence"])
    else:
        if simulated_profile["Gender"] == "Male":
            profile_desc = "a retired man in the age range of {}, living in {}".format(simulated_profile["Age Range"].lower(), simulated_profile["Residence"])
        else:
            profile_desc = "a retired woman in the age range of {}, living in {}".format(simulated_profile["Age Range"].lower(), simulated_profile["Residence"])
    user_desc += profile_desc + ".\n\n"
    
    user_desc += "Based on your past experiences, you have the following preferences:\n"
    if domain == "movie" or domain == "music":
        for k in ["Accepted movies", "Accepted music", "Accepted celebrities", "Rejected movies", "Rejected music"]:
            kk = k.replace("Accepted", "liked").replace("Rejected", "disliked")
            user_desc += "Your {}: {}.\n".format(kk, simulated_profile[k]) if simulated_profile.get(k, "") != "" else ""
    else:
        for k in ["Accepted food", "Accepted POI"]:
            kk = k.replace("Accepted", "liked")
            user_desc += "Your {}: {}.\n".format(kk, simulated_profile[k]) if simulated_profile.get(k, "") != "" else ""
    user_desc += "\n"

    
    user_desc += "Based on the Big-5 personality traits, your personality is measured as:\n"
    for k, v in simulated_personality.items():
        user_desc += "For {}, you are {}.\n".format(k, v)
    user_desc += "\n"

    user_desc += "Your response should match your profile and personality, and be concise (no longer than 30 words).\n"
    user_desc += "You don't need to recommend anything, but feel free to express your personal interests."

    gender_desc = "his" if simulated_profile["Gender"] == "Male" else "her"
    if domain == "movie" or domain == "music":
        for k in ["Accepted movies", "Accepted music", "Accepted celebrities", "Rejected movies", "Rejected music"]:
            kk = k.replace("Accepted", "liked").replace("Rejected", "disliked")
            profile_desc += "; {} {}: {}".format(gender_desc, kk, simulated_profile[k]) if simulated_profile.get(k, "") != "" else ""
    else:
        for k in ["Accepted food", "Accepted POI"]:
            kk = k.replace("Accepted", "liked")
            profile_desc += "; {} {}: {}".format(gender_desc, kk, simulated_profile[k]) if simulated_profile.get(k, "") != "" else ""
    profile_desc += "."

    user_dict = {
        "name": simulated_profile["Name"],
        "role_desc": user_desc,
    }
    
    # Describe the assistant
    if domain == "movie":
        assistant_desc = "You are {}, a movie enthusiast who enjoys a variety of films.\n".format(assistant_name)
    elif domain == "music":
        assistant_desc = "You are {}, a music enthusiast who enjoys a variety of music.\n".format(assistant_name)
    elif domain == "food":
        assistant_desc = "You are {}, a foodie who enjoys delicious food.\n".format(assistant_name)
    elif domain == "poi":
        assistant_desc = "You are {}, a food enthusiast who is interested in exploring different restaurants.\n".format(assistant_name)
    else:
        raise ValueError("Invalid domain: {}".format(domain))
    
    assistant_desc += "You are conversing with {}, whose profile is below: \n## {}\n\n".format(simulated_profile["Name"], profile_desc)
    assistant_desc += "Your goal is to proactively lead the conversation with {} towards the target {} \"{}\".\n".format(simulated_profile["Name"], domain, target[1])
    assistant_desc += "To start the conversation, please begin with a greeting and avoid mentioning the target {}.\n".format(domain)
    assistant_desc += "As the conversation progresses, use your domain knowledge to steer the discussed topic towards the target {} step by step.\n".format(domain)
    assistant_desc += "Be informative and engaging while providing insights to arouse {}'s interest.\n".format(simulated_profile["Name"])
    assistant_desc += "Remember to ultimately recommend \"{}\" as the focus of the conversation.\n".format(target[1])
    assistant_desc += "Your words at each turn should be concise (no longer than 30 words).\n\n"
    assistant_desc += "You may access the following domain knowledge for conversation: \n## {}.".format(domain_knowledge)

    assistant_dict = {
        "name": assistant_name,
        "role_desc": assistant_desc,
    }
    
    # Describe the moderator
    moderator_desc = "You are the moderator of a conversation. You need to determine whether the discussion between Role-S and Role-U should come to an immediate end.\n"
    moderator_desc += "The conversation should conclude under the following two conditions:\n"
    moderator_desc += "(1) If Role-S completes {} recommendation on \"{}\" and Role-U accepts it, and Role-S no longer takes the initiative for two rounds.\n".format(domain, target[1])
    moderator_desc += "(2) If Role-U explicitly rejects Role-S's recommendation on \"{}\" when Role-S has tried to recommend it for the second time.\n".format(target[1])
    moderator_desc += "In either of these cases, the conversation should be brought to an immediate end.\n\n"

    moderator_desc += "For example, here is a conversation:\n## {}".format(seed_conversation["seed_continue"])
    moderator_desc += "Should the conversation end? The answer is no.\n\n"
    moderator_desc += "Here is another conversation:\n## {}".format(seed_conversation["seed_end"])
    moderator_desc += "Should the conversation end? The answer is yes."

    
    terminal_condition = "Now, for the above discussion between {} (Role-S) and {} (Role-U), should the conversation end? Answer yes or no.".format(assistant_name, simulated_profile["Name"])

    moderator_dict = {
        "role_desc": moderator_desc,
        "terminal_condition": terminal_condition
    }

    return (env_desc, user_dict, assistant_dict, moderator_dict)
