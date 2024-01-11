#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import json
import numpy as np
from collections import Counter
import nltk
from nltk.translate import bleu_score
from nltk.translate.bleu_score import SmoothingFunction


def calc_bleu(hyps, refs):
    """ Calculate bleu score """
    bleu_1 = []
    bleu_2 = []
    for hyp, ref in zip(hyps, refs):
        try:
            score = bleu_score.sentence_bleu(
                [ref], hyp,
                smoothing_function=SmoothingFunction().method1,
                weights=[1, 0, 0, 0])
        except:
            score = 0
        bleu_1.append(score)
        try:
            score = bleu_score.sentence_bleu(
                [ref], hyp,
                smoothing_function=SmoothingFunction().method1,
                weights=[0, 1, 0, 0])
        except:
            score = 0
        bleu_2.append(score)
    bleu_1 = np.average(bleu_1)
    bleu_2 = np.average(bleu_2)
    avg_bleu = (bleu_1 + bleu_2) / 2
    return bleu_1, bleu_2, avg_bleu


def calc_knowledge_f1(hyps, knowledge_refs, knowledge_alls):
    """" Calculate knowledge f1 score """
    golden_total = 0.0
    pred_total = 0.0
    hit_total = 0.0
    for response, golden_kd, all_kd in zip(hyps, knowledge_refs, knowledge_alls):
        golden_total += len(golden_kd)
        for kd in golden_kd:
            if is_obj_hit(response, kd):
                hit_total += 1
        for kd in all_kd:
            if is_obj_hit(response, kd):
                pred_total += 1
    p = hit_total / pred_total if pred_total > 0 else 0
    r = hit_total / golden_total if golden_total > 0 else 0
    f1 = 2 * p * r / (p + r) if p + r > 0 else 0
    return f1


def calc_persona_f1(hyps, persona_refs, persona_alls):
    """Calculate persona f1 score"""
    golden_total = 0.0
    pred_total = 0.0
    hit_total = 0.0
    for response, golden_persona, all_persona in zip(hyps, persona_refs, persona_alls):
        golden_total += len(golden_persona)
        for persona in golden_persona:
            if is_obj_hit(response, persona, threshold=0.8):
                hit_total += 1
        for persona in all_persona:
            if is_obj_hit(response, persona, threshold=0.8):
                pred_total += 1
    p = hit_total / pred_total if pred_total > 0 else 0
    r = hit_total / golden_total if golden_total > 0 else 0
    f1 = 2 * p * r / (p + r) if p + r > 0 else 0
    return f1

def calc_succ(eval_fp, gold_fp):
    all_eval, all_gold = [], []
    with open(eval_fp, 'r', encoding='utf-8') as fr:
        for line in fr:
            sample = json.loads(line)
            all_eval.append(sample)
    with open(gold_fp, 'r', encoding='utf-8') as fr:
        for line in fr:
            raw_sample = json.loads(line)
            sample = {
                "id": raw_sample["id"],
                "target": raw_sample["target"],
                "response": raw_sample["response"]
            }
            all_gold.append(sample)
    assert len(all_eval) == len(all_gold)

    topic_hit, topic_total = 0, 0
    movie_hit, music_hit, poi_hit, food_hit = 0, 0, 0, 0
    movie_total, music_total, poi_total, food_total = 0, 0, 0, 0
    
    for idx, gold_sample in enumerate(all_gold):
        if gold_sample["target"][1].lower() in gold_sample["response"].lower():
            topic_total += 1
            eval_action = gold_sample["target"][0]
            eval_topic = gold_sample["target"][1]
            
            # eval target turn and neighboring turns
            eval_list = get_eval_response(idx, all_eval, all_gold)
            
            eval_topic = " ".join(nltk.word_tokenize(eval_topic))
            eval_list = [" ".join(nltk.word_tokenize(eval_response)) for eval_response in eval_list]
            
            if is_topic_hit(eval_topic, eval_list):
                topic_hit += 1
            
            if eval_action == "Movie recommendation":
                movie_total += 1
                if is_topic_hit(eval_topic, eval_list):
                    movie_hit += 1
            elif eval_action == "Music recommendation" or eval_action == "Play music":
                music_total += 1
                if is_topic_hit(eval_topic, eval_list):
                    music_hit += 1
            elif eval_action == "POI recommendation":
                poi_total += 1
                if is_topic_hit(eval_topic, eval_list):
                    poi_hit += 1
            elif eval_action == "Food recommendation":
                food_total += 1
                if is_topic_hit(eval_topic, eval_list):
                    food_hit += 1
    succ_rate = float(topic_hit) / topic_total
    movie_rec_sr = float(movie_hit) / movie_total
    music_rec_sr = float(music_hit) / music_total
    poi_rec_sr = float(poi_hit) / poi_total
    food_rec_sr = float(food_hit) / food_total
    print("Succ.: {:.2f}%".format(succ_rate*100))
    print("Succ.-Movie: {}/{} = {:.2f}%".format(movie_hit, movie_total, movie_rec_sr*100))
    print("Succ.-Music: {}/{} = {:.2f}%".format(music_hit, music_total, music_rec_sr*100))
    print("Succ.-POI: {}/{} = {:.2f}%".format(poi_hit, poi_total, poi_rec_sr*100))
    print("Succ.-Food: {}/{} = {:.2f}%".format(food_hit, food_total, food_rec_sr*100))


def get_eval_response(idx, eval_samples, gold_samples):
    eval_list = [eval_samples[idx]["response"]]
    dialog_id = gold_samples[idx]["id"]
    if idx - 1 >= 0 and gold_samples[idx-1]["id"] == dialog_id:
        eval_list.append(eval_samples[idx-1]["response"])
    if idx + 1 < len(gold_samples) and gold_samples[idx+1]["id"] == dialog_id:
        eval_list.append(eval_samples[idx+1]["response"])
    return eval_list

def is_topic_hit(topic, candidates):
    for cand in candidates:
        if topic.lower() in cand.lower():
            return True
    return False

def is_obj_hit(utterance_toks, obj_str, threshold=0.55):
    utterance = " ".join(utterance_toks)
    flag = False
    if obj_str in utterance:
        flag = True
    else:
        # English word-level
        common = Counter(utterance.split()) & Counter(obj_str.split())
        # knowledge recall
        hit_char_total = sum(common.values())
        golden_char_total = len(obj_str)
        recall = hit_char_total / golden_char_total if golden_char_total > 0 else 0
        if recall >= threshold:
            flag = True
    return flag

def label_knowledge(utterance_toks, kg_list, lower_case=True):
    gold_knowledge = []
    all_objs = set()
    for triple in kg_list:
        assert len(triple) == 3
        all_objs.add(triple[0].lower() if lower_case else triple[0])
        all_objs.add(triple[2].lower() if lower_case else triple[2])
    for obj in all_objs:
        if is_obj_hit(utterance_toks, obj):
            gold_knowledge.append(obj)
    all_objs = list(all_objs)
    return all_objs, gold_knowledge

def label_persona(utterance_toks, persona_dict, lower_case=True):
    all_personas = []
    gold_persona = []
    for k, v in persona_dict.items():
        if v != '' and v != ' ':
            all_personas.append(v.lower() if lower_case else v)
    for persona in all_personas:
        if is_obj_hit(utterance_toks, persona, threshold=0.8):
            gold_persona.append(persona)
    return all_personas, gold_persona


def load_data(fp, is_gold=False, lower_case=True):
    samples = []
    all_knowledges, gold_knowledges = [], []
    all_personas, gold_personas = [], []
    with open(fp, 'r', encoding='utf-8') as fr:
        for idx, line in enumerate(fr):
            sample = json.loads(line)
            response = sample["response"].lower() if lower_case else sample["response"]
            # English word-level
            sentence_toks = nltk.word_tokenize(response)
            samples.append(sentence_toks)
            if is_gold:
                knowledge = sample["knowledge"]
                all_k, all_k= label_knowledge(sentence_toks, knowledge, lower_case=lower_case)
                all_knowledges.append(all_k)
                gold_knowledges.append(all_k)
                persona = sample["user_profile"]
                all_p, gold_p = label_persona(sentence_toks, persona, lower_case=lower_case)
                all_personas.append(all_p)
                gold_personas.append(gold_p)
    if is_gold:
        assert len(samples) == len(all_knowledges) and \
            len(samples) == len(gold_knowledges) and \
            len(samples) == len(all_personas)
        return (samples, all_knowledges, gold_knowledges, all_personas, gold_personas)
    else:
        return samples


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval_file", type=str)
    parser.add_argument("--gold_file", type=str)
    args = parser.parse_args()

    preds = load_data(args.eval_file)
    refs, all_knowledges, ref_knowlwedges, all_peronas, ref_personas = load_data(args.gold_file, is_gold=True)
    assert len(preds) == len(refs)

    # calculate bleu
    bleu1, bleu2, avg_bleu = calc_bleu(preds, refs)

    # calculate knowledge-F1
    kg_f1 = calc_knowledge_f1(preds, ref_knowlwedges, all_knowledges)

    # calculate persona-F1
    persona_f1 = calc_persona_f1(preds, ref_personas, all_peronas)

    output_str = "Avg. BLEU: %.3f\n" % avg_bleu
    output_str += "Knowledge F1: %.2f%%\n" % (kg_f1 * 100)
    output_str += "Persona F1: %.2f%%" % (persona_f1 * 100)

    print(output_str)

    # calculate target success
    calc_succ(args.eval_file, args.gold_file)
