# -*- coding: utf-8 -*-
import re
import random


def find_word_in_string(w, s):
    return re.compile(r"\b({0})\b".format(w), flags=re.IGNORECASE).search(s)

def normalize_profile(profile: dict, domain: str):
    """Nomalize profile based on specific domain"""
    norm_profile = {}
    for slot_k, slot_value in profile.items():
        if slot_k == "Age Range":
            norm_profile[slot_k] = slot_value.replace("years old", "").strip()
        elif slot_k == "Accepted Music":   # mismatched slot key in raw data
            if "Accepted music" in norm_profile.keys():
                norm_profile["Accepted music"] += "; " + slot_value
            else:
                norm_profile["Accepted music"] = slot_value
        elif slot_k == "Accepted movie":   # mismatched slot key in raw data
            if "Accepted movies" in norm_profile.keys():
                norm_profile["Accepted movies"] += "; " + slot_value
            else:
                norm_profile["Accepted movies"] = slot_value
        else:
            if slot_k in norm_profile.keys():
                norm_profile[slot_k] += "; " + slot_value
            else:
                norm_profile[slot_k] = slot_value
    
    for slot_k, slot_v in norm_profile.items():
        if "Accepted" in slot_k or "Rejected" in slot_k:
            if len(slot_v.split("; ")) > 2:
                norm_profile[slot_k] = "; ".join(slot_v.split("; ")[:2])

    # remove unnecessary slots for a specific domain
    assert domain in ["movie", "music", "food", "poi"]
    if "Accepted news" in norm_profile.keys():
        norm_profile.pop("Accepted news")
    if "Favorite news" in norm_profile.keys():
        norm_profile.pop("Favorite news")
    if "Reject" in norm_profile.keys():
        norm_profile.pop("Reject")
    
    if domain == "food" or domain == "poi":
        if "Accepted movies" in norm_profile.keys():
            norm_profile.pop("Accepted movies")
        if "Accepted music" in norm_profile.keys():
            norm_profile.pop("Accepted music")
        if "Accepted celebrities" in norm_profile.keys():
            norm_profile.pop("Accepted celebrities")
        if "Rejected movies" in norm_profile.keys():
            norm_profile.pop("Rejected movies")
        if "Rejected music" in norm_profile.keys():
            norm_profile.pop("Rejected music")
    else:
        if "Accepted food" in norm_profile.keys():
            norm_profile.pop("Accepted food")
        if "Accepted POI" in norm_profile.keys():
            norm_profile.pop("Accepted POI")

    return norm_profile


def sample_profile(profile_slots, target_topic, domain):
    """Sample a profile different from raw_profile."""
    sampled_profile = {}
    for slot_key, slot_values in profile_slots.items():
        sampled_value = random.choice(slot_values)
        while sampled_value in target_topic or target_topic in sampled_value:
            sampled_value = random.choice(slot_values)
        sampled_profile[slot_key] = sampled_value
    # check age range and occupation
    if sampled_profile["Age Range"] == "Under 18":
        sampled_profile["Occupation"] = "Student"
    elif sampled_profile["Age Range"] == "18-25" or sampled_profile["Age Range"] == "26-35":
        sampled_profile["Occupation"] = random.choice(["Student", "Employed"])
    elif sampled_profile["Age Range"] == "36-50":
        sampled_profile["Occupation"] = "Employed"
    else:
        sampled_profile["Occupation"] = random.choice(["Employed", "Retired"])
    
    normed_profile = normalize_profile(sampled_profile, domain)
    return normed_profile


def check_kg_exceed(kg_list, max_len):
    limit_len = max_len - len(kg_list)
    kg_str = " ".join([" ".join(kg) for kg in kg_list])
    kg_tokens = kg_str.split(" ")
    if len(kg_tokens) > limit_len:
        return True
    else:
        return False

def check_topic_covered(sampled_kg, topic_path):
    sampled_objs = set()
    for triple in sampled_kg:
        s, p, o = triple
        sampled_objs.add(s)
        sampled_objs.add(o)
    is_covered = True
    for t in topic_path:
        if t != "NULL" and t not in sampled_objs:
            is_covered = False
            break
    return is_covered

def get_outer_kg(kg_list, sampled_kg, topic_path):
    topic_list = []
    for t in topic_path:
        if t != "NULL":
            topic_list.append(t)
 
    sampled_objs = set()
    for triple in sampled_kg:
        s, p, o = triple
        sampled_objs.add(s)
        sampled_objs.add(o)
    
    tmp_kg = {}
    for t in topic_list:
        if t not in sampled_objs:
            for triple in kg_list:
                s, p, o = triple
                if s == t:
                    if s in tmp_kg:
                        tmp_kg[s].append(triple)
                    else:
                        tmp_kg[s] = [triple]
                elif o == t:
                    if o in tmp_kg:
                        tmp_kg[o].append(triple)
                    else:
                        tmp_kg[o] = [triple]
    outer_kg = []
    for k, v_list in tmp_kg.items():
        spo = random.sample(v_list, 1)
        outer_kg.append(spo[0]) 
    
    return outer_kg

def sample_knowledge(raw_kg_list, target, topic_path, user_utt="", bot_utt="", max_len=300):
    kg_list = []
    for kg in raw_kg_list:
        s, p, o = kg
        if p == "Stars":
            if len(o.split()) <= 40:
                kg_list.append(kg)
        else:
            kg_list.append(kg)
    
    topic_trans = []
    kg_topic_path = []
    for t in topic_path:
        if t != "NULL":
            kg_topic_path.append(t)
    if len(kg_topic_path) > 1:
        for j in range(1, len(kg_topic_path)-1):
            topic_trans.append([kg_topic_path[j], kg_topic_path[j-1]])

    sampled_kg = []
    for kg in kg_list:
        s, p, o = kg

        if target[0] == "Food recommendation" and target[1] == "Marinated Fish" and p == "Specials" and o == "Marinated Fish":
            pass
        elif s == target[1] or o == target[1]:
            if not kg in sampled_kg:
                sampled_kg.append(kg)
        if "℃" in o and "℃" in bot_utt:
            if not kg in sampled_kg:
                sampled_kg.append(kg)
        if p == "Perfect for having" and (o.lower() in user_utt.lower() or o.lower() in bot_utt.lower()):
            if not kg in sampled_kg:
                sampled_kg.append(kg)
        if p.lower() in user_utt.lower() or p.lower() in bot_utt.lower():
            if p == "Sings" and s == topic_path[0]:
                pass
            elif p == "Achievement" and s == topic_path[0]:
                if o.lower() in bot_utt.lower():
                    if not kg in sampled_kg:
                        sampled_kg.append(kg)
            elif p == "Awards" and s == topic_path[0]:
                if o.lower() in bot_utt.lower():
                    if not kg in sampled_kg:
                        sampled_kg.append(kg)
            else:
                if s == topic_path[0] or o == topic_path[0]:
                    if not kg in sampled_kg:
                        sampled_kg.append(kg)
        if s == topic_path[0]:
            if o.lower() in bot_utt.lower():
                if not kg in sampled_kg:
                    sampled_kg.append(kg)
        for tp in topic_trans:
            src, tgt = tp
            if (src == s and tgt in o) or (src in o and tgt == s):
                if not kg in sampled_kg:
                    sampled_kg.append(kg)
    # check which topic not in sampled knowledge
    outer_kg = get_outer_kg(kg_list, sampled_kg, topic_path)
    if len(outer_kg) > 0:
        sampled_kg += outer_kg
    
    noised_kg = []
    for kg in kg_list:
        if not kg in sampled_kg:
            noised_kg.append(kg)
    random.shuffle(noised_kg)
    
    num_spling = 1
    tmp_kg = []
    while True:
        if num_spling > len(noised_kg):
            break
        tmp_kg = random.sample(noised_kg, num_spling)
        check_kg = sampled_kg + tmp_kg
        if check_kg_exceed(check_kg, max_len=max_len):
            break
        num_spling += 1
    sampled_kg += tmp_kg[:-1]
    random.shuffle(sampled_kg)
    
    return sampled_kg