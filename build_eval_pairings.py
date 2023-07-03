#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import json
import os
import random


def clean_utterance(s):
    s = s.strip()
    for start_str in ['[1]', '[2]', '[3]', '[4]', '[5]', '[6]', '[7]', '[8]', '[9]']:
        if s.startswith(start_str):
            s = s[len(start_str):].strip()
    return s

def load_data(data_dr, data_part="train"):
    data = []
    with open("{}/dialogue_{}.jsonl".format(data_dr, data_part), "r", encoding='utf-8') as fr:
        for line in fr:
            data.append(json.loads(line.strip()))
    return data

def sample_seed_data(seed_dir, sample_num=100):
    seed_train = load_data(seed_dir, data_part="train")
    seed_dev = load_data(seed_dir, data_part="dev")
    seed_test_seen = load_data(seed_dir, data_part="test_seen")
    seed_test_unseen = load_data(seed_dir, data_part="test_unseen")
    seed_all = seed_train + seed_dev + seed_test_seen + seed_test_unseen

    target2dialog = {}
    target_keys = set()
    for dialog in seed_all:
        target = "__SEP__".join(dialog['target'])
        target_keys.add(target)
        if target not in target2dialog:
            target2dialog[target] = [dialog]
        else:
            target2dialog[target].append(dialog)
    sampled_target_keys = random.sample(list(target_keys), sample_num)
    
    sampled_dialogs ={}
    for target in sampled_target_keys:
        s_dialog = random.choice(target2dialog[target])
        raw_goal = s_dialog['original_goal']
        raw_conv = s_dialog['conversation']
        new_conv = []
        for idx, utt in enumerate(raw_conv):
            utt = clean_utterance(utt)
            if "User Initiative" in raw_goal:
                if idx % 2 == 0:
                    new_conv.append({"user": utt})
                else:
                    new_conv.append({"system": utt})
            else:
                if idx % 2 == 0:
                    new_conv.append({"system": utt})
                else:
                    new_conv.append({"user": utt})
        sampled_dialogs[target] = new_conv
    print("Seed sampled_dialogs: {}".format(len(sampled_dialogs)))
    return sampled_target_keys, sampled_dialogs


def sample_ours_data(ours_dir, sampled_targets):
    ours_train = load_data(ours_dir, data_part="train")
    ours_dev = load_data(ours_dir, data_part="dev")
    ourstest_seen = load_data(ours_dir, data_part="test_seen")
    ours_test_unseen = load_data(ours_dir, data_part="test_unseen")
    ours_all = ours_train + ours_dev + ourstest_seen + ours_test_unseen
    
    target2dialog = {}
    for dialog in ours_all:
        target = "__SEP__".join(dialog['target'])
        if target not in target2dialog:
            target2dialog[target] = [dialog]
        else:
            target2dialog[target].append(dialog)
    
    sampled_dialogs = {}
    for target in sampled_targets:
        s_dialog = random.choice(target2dialog[target])
        sampled_dialogs[target] = s_dialog["conversation"]
    print("Ours sampled_dialogs: {}".format(len(sampled_dialogs)))
    return sampled_dialogs


def create_eval(seed_dir, ours_dir, save_dir, seed=40):
    random.seed(seed)

    sampled_targets, seed_sampled_dialogs = sample_seed_data(seed_dir, sample_num=100)
    ours_sampled_dialogs = sample_ours_data(ours_dir, sampled_targets)

    all_pairs = []
    for k_target, v_seed in seed_sampled_dialogs.items():
        seed_dialog = []
        for utt in v_seed:
            if "system" in utt:
                text = utt["system"]
                k = "system_seed"
            else:
                text = utt["user"]
                k = "user"
            seed_dialog.append({"id": k, "text": text})
        seed_dict = {
            "speakers": ["system_seed", "human"],
            "dialogue": seed_dialog
        }
        v_ours = ours_sampled_dialogs[k_target]
        ours_dialog = []
        for utt in v_ours:
            if "system" in utt:
                text = utt["system"]
                k = "system_ours"
            else:
                text = utt["user"]
                k = "user"
            ours_dialog.append({"id": k, "text": text})
        ours_dict = {
            "speakers": ["system_ours", "human"],
            "dialogue": ours_dialog
        }
        pair = {
            "is_onboarding": False,
            "speakers_to_eval": ["system_seed", "system_ours"],
            "dialogue_target": k_target.split("__SEP__"),
            "dialogue_ids": [0, 1],
            "dialogue_dicts": [seed_dict, ours_dict]
        }
        all_pairs.append(pair)
    
    save_path = os.path.join(save_dir, "eval_pairs.jsonl")
    with open(save_path, 'w', encoding='utf-8') as fw:
        for sample in all_pairs:
            fw.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print("saved to {}".format(save_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed_dir", type=str)
    parser.add_argument("--ours_dir", type=str)
    parser.add_argument("--save_dir", type=str)
    parser.add_argument("--random_seed", type=int, default=40)
    args = parser.parse_args()

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)
    create_eval(args.seed_dir, args.ours_dir, args.save_dir, args.random_seed)
