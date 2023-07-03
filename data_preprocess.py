# -*- coding: utf-8 -*-
import json
import os
import random
import argparse
from tqdm import tqdm
from py2neo import Graph
from data_utils import normalize_profile, sample_profile, sample_knowledge


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--seed_dataset_dir",
        type=str,
        default="seed_dataset/DuRecDial2",
        help="The seed dataset directory."
    )
    parser.add_argument(
        "--cache_dir",
        type=str,
        default="seed_dataset/caches",
        help="The cached data directory."
    )
    parser.add_argument(
        "--num_instance_per_seed",
        type=int,
        default=3,
        help="The number of instances to curate for each seed dialog.",
    )
    parser.add_argument(
        "--random_seed",
        type=int,
        default=42,
    )
    return parser.parse_args()


def extract_profile(data_fp_list, save_fp=None):
    """Extract all user profile slots from the given data file."""
    
    SLOT_KEYS = [
        "Age Range", "Name", "Gender", "Residence", "Occupation", "POI",
        "Accepted movies", "Accepted music", "Accepted celebrities", "Accepted food", "Accepted POI", 
        "Reject", "Rejected movies", "Rejected music"
        ]
    ALL_SLOTS = dict()
    for k in SLOT_KEYS:
        ALL_SLOTS[k] = set()

    for data_fp in data_fp_list:
        with open(data_fp, 'r', encoding='utf-8') as fp:
            for line in fp:
                sample = json.loads(line.strip())
                for slot in sample['user_profile']:
                    if slot in SLOT_KEYS:
                        slot_value = list(sample['user_profile'][slot].split("; "))
                        for v in slot_value:
                            if slot == "Age Range":
                                v = v.replace("years old", "").strip()
                            ALL_SLOTS[slot].add(v)
                    elif slot == "Accepted Music":
                        slot_value = list(sample['user_profile'][slot].split("; "))
                        for v in slot_value:
                            ALL_SLOTS["Accepted music"].add(v)
                    elif slot == "Accepted movie":
                        slot_value = list(sample['user_profile'][slot].split("; "))
                        for v in slot_value:
                            ALL_SLOTS["Accepted movies"].add(v)
                    else:
                        print("Out of slot keys: ", slot)
    for k in ALL_SLOTS:
        ALL_SLOTS[k] = list(ALL_SLOTS[k])
        print(k, len(ALL_SLOTS[k]))
    if save_fp is not None:
        with open(save_fp, 'w', encoding='utf-8') as fp:
            json.dump(ALL_SLOTS, fp, indent=4, ensure_ascii=False)
        print("Saved to {}".format(save_fp))


def exe_query(graph: Graph, query: str):
    triple_dict = {}
    results = graph.run(query).data()
    for res in results:
        s = "{}".format(res['s.value'])
        r = "{}".format(res['type(r)'])
        o = "{}".format(res['o.value'])
        kk = "{}__REL__{}".format(s, r)
        if kk in triple_dict.keys():
            triple_dict[kk].append(o)
        else:
            triple_dict[kk] = [o]
    triples = []
    for kk, vv in triple_dict.items():
        s, r = kk.split("__REL__")
        o = random.choice(vv)
        triples.append([s, r, o])
    
    return triples

def ground_knowledge(graph, data_fp_list, profile_fp, save_dir, num_instance_per_seed=3):
    """Ground seed dialogs with domain knowledge and comments."""
    
    profile_slots = json.load(open(profile_fp, "r", encoding='utf-8'))
    print(f"Loaded user profiles with {len(profile_slots)} slot keys.")

    for data_fp in data_fp_list:
        seed_dialogs = []
        with open(data_fp, "r", encoding='utf-8') as f:
            for line in f:
                seed_dialogs.append(json.loads(line))
        print(f"Loaded {len(seed_dialogs)} seed dialogs from {data_fp}.")
        
        save_fp = os.path.join(save_dir, "cache_{}".format(data_fp.split("/")[-1]))
        with open(save_fp, "w", encoding='utf-8') as fw:
            for seed_dialog in tqdm(seed_dialogs):
                user_profile = seed_dialog["user_profile"]
                knowledge = seed_dialog["knowledge_graph"]
                target = seed_dialog["target"]

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

                for idx in range(num_instance_per_seed):
                    if idx == 0:
                        # adopt raw user profile
                        simulated_profile = normalize_profile(user_profile, domain)
                    else:
                        # sample a profile different from raw user profile
                        simulated_profile = sample_profile(profile_slots, target_topic=target[1], domain=domain)

                    sampled_knowledge = sample_knowledge(knowledge, target, topic_path=seed_dialog["topic_path"], max_len=300)

                    # sample comment about the target topic
                    query_t = 'MATCH (s)-[r]->(o) WHERE s.value="{}" AND type(r)="{}" RETURN s.value, type(r), o.value'.format(target[1], "Comments")
                    target_comments = exe_query(graph, query_t)
                    if len(target_comments) > 0:
                        target_comment = random.choice(target_comments)
                        sampled_knowledge.append(target_comment)

                    profile_knowledge = []
                    for slot_key, slot_value in simulated_profile.items():
                        if "movies" in slot_key or "music" in slot_key:
                            # sample domain knowledge about movies/music
                            entities = slot_value.split("; ")
                            for ent in entities:
                                query_t = 'MATCH (s)-[r]->(o) WHERE s.value="{}" AND (type(r)="{}" OR type(r)="{}" OR type(r)="{}" OR type(r)="{}") RETURN s.value, type(r), o.value'.format(
                                    ent, "Stars", "Sings", "Type", "Comments")
                                triples = exe_query(graph, query_t)
                                if len(triples) > 0:
                                    ss_triples = random.choice(triples)
                                    profile_knowledge.append(ss_triples)
                        elif "celebrities" in slot_key:
                            # sample domain knowledge about celebrities
                            entities = slot_value.split("; ")
                            for ent in entities:
                                query_t = 'MATCH (s)-[r]->(o) WHERE s.value="{}" AND (type(r)="{}" OR type(r)="{}" OR type(r)="{}") RETURN s.value, type(r), o.value'.format(
                                    ent, "Intro", "Achievement", "Comments")
                                triples = exe_query(graph, query_t)
                                if len(triples) > 0:
                                    ss_triples = random.choice(triples)
                                    profile_knowledge.append(ss_triples)
                        elif "food" in slot_key or "Accepted POI" in slot_key:
                            # sample domain knowledge about food/POI
                            entities = slot_value.split("; ")
                            for ent in entities:
                                query_t = 'MATCH (s)-[r]->(o) WHERE s.value="{}" AND (type(r)="{}" OR type(r)="{}" OR type(r)="{}" OR type(r)="{}") RETURN s.value, type(r), o.value'.format(
                                    ent, "Price per person", "Rating", "Address", "Comments")
                                triples = exe_query(graph, query_t)
                                if len(triples) > 0:
                                    ss_triples = random.choice(triples)
                                    profile_knowledge.append(ss_triples)
                    knowledge_str_list = ["__SEP__".join(triple) for triple in sampled_knowledge]
                    for triple in profile_knowledge:
                        triple_str = "__SEP__".join(triple)
                        if triple_str not in knowledge_str_list:
                            sampled_knowledge.append(triple)

                    new_dialog = {
                        "id": str(seed_dialog["id"]) + "_{}".format(idx),
                        "original_goal": seed_dialog["original_goal"],
                        "user_profile": simulated_profile,
                        "knowledge": sampled_knowledge,
                        "target": target,
                        "seed_conversation": seed_dialog["conversation"],
                        "seed_action_path": seed_dialog["action_path"],
                        "seed_topic_path": seed_dialog["topic_path"],
                    }
                    line = json.dumps(new_dialog, ensure_ascii=False)
                    fw.write(line + "\n")
                    fw.flush()
        print("Saved {} simulated dialogs to {}.".format(num_instance_per_seed * len(seed_dialogs), save_fp))       


if __name__ == "__main__":
    args = parse_args()
    random.seed(args.random_seed)

    train_fp = os.path.join(args.data_dir, "seed_dialogue_train.jsonl")
    dev_fp = os.path.join(args.data_dir, "seed_dialogue_dev.jsonl")
    test_seen_fp = os.path.join(args.data_dir,"seed_dialogue_test_seen.jsonl")
    test_unseen_fp = os.path.join(args.data_dir, "seed_dialogue_test_unseen.jsonl")

    if not os.path.exists(args.cache_dir):
        os.makedirs(args.cache_dir)

    # prepare user profile slots
    saved_dir = os.path.join(args.cache_dir, "db_slot")
    if not os.path.exists(saved_dir):
        os.makedirs(saved_dir)

    saved_profile_fp = os.path.join(saved_dir, "slot_profiles.json")
    if not os.path.exists(saved_profile_fp):
        print("Extracting user profile slot-values...")
        extract_profile(data_fp_list=[train_fp, dev_fp, test_seen_fp, test_unseen_fp], save_fp=saved_profile_fp)
    else:
        print("File exists: {}".format(saved_profile_fp))
    
    # prepare domain knowledge and topic-related comments
    # set neo4j database connection (username: neo4j, password: neo4j)
    graph = Graph("http://localhost:7474", auth=("neo4j", "neo4j"))
    ground_knowledge(graph, data_fp_list=[train_fp, dev_fp, test_seen_fp, test_unseen_fp],
                     profile_fp=saved_profile_fp, save_dir=args.cache_dir, 
                     num_instance_per_seed=args.num_instance_per_seed)