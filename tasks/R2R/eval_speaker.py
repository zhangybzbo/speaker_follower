''' Evaluation of agent trajectories '''

import json
import pprint
pp = pprint.PrettyPrinter(indent=4)

import utils
from utils import load_datasets, Tokenizer
import numpy as np
from bleu import multi_bleu

class SpeakerEvaluation(object):
    ''' Results submission format:  [{'instr_id': string, 'trajectory':[(viewpoint_id, heading_rads, elevation_rads),] } ] '''

    def __init__(self, splits):
        self.splits = splits
        self.gt = {}
        self.instr_ids = []
        self.scans = []

        for item in load_datasets(splits):
            self.gt[item['path_id']] = item
            self.scans.append(item['scan'])
            self.instr_ids += ['%d_%d' % (item['path_id'],i) for i in range(3)]

        self.scans = set(self.scans)
        self.instr_ids = set(self.instr_ids)

    def score_results(self, results, verbose=False):
        # results should be a dictionary mapping instr_ids to dictionaries, with each dictionary containing (at least) a 'words' field
        instr_ids = set(self.instr_ids)

        instr_count = 0

        results_by_base_id = {}

        for instr_id, result in results.items():
            if instr_id in instr_ids:
                instr_count += 1
                instr_ids.remove(instr_id)

                base_id = int(instr_id.split('_')[0])

                if base_id in results_by_base_id:
                    assert results_by_base_id[base_id]['words'] == result['words']
                else:
                    results_by_base_id[base_id] = result

        assert len(instr_ids) == 0, 'Missing %d of %d instruction ids from %s' \
                                    % (len(instr_ids), len(self.instr_ids), ",".join(self.splits))

        all_refs = []
        all_hyps = []

        model_scores = []

        skip_count = 0
        skipped_refs = set()
        for base_id, result in sorted(results_by_base_id.items()):
            gt = self.gt[base_id]
            tokenized_refs = [Tokenizer.split_sentence(ref) for ref in gt['instructions']]
            if len(tokenized_refs) != 3:
                skip_count += 1
                skipped_refs.add(base_id)
                continue
            tokenized_hyp = result['words']
            all_refs.append(tokenized_refs)
            all_hyps.append(tokenized_hyp)

            if 'score' in result:
                model_scores.append(result['score'])

            if verbose and instr_count % 100 == 0:
                for i, ref in enumerate(tokenized_refs):
                    print("ref {}:\t{}".format(i, ' '.join(ref)))
                print("pred  :\t{}".format(' '.join(tokenized_hyp)))
                print()

        if skip_count != 0:
            print("skipped {} instructions without 3 refs: {}".format(skip_count, ' '.join(str(i) for i in skipped_refs)))

        model_score = np.mean(model_scores)
        bleu, unpenalized_bleu = multi_bleu(all_refs, all_hyps)

        score_summary = {
            'model_score': model_score,
            'bleu': bleu,
            'unpenalized_bleu': unpenalized_bleu,
        }
        return score_summary

    def score_file(self, output_file, verbose=False):
        ''' Evaluate each agent trajectory based on how close it got to the goal location '''
        with open(output_file) as f:
            return self.score_results(json.load(f), verbose=verbose)


def eval_seq2seq():
    import train_speaker
    outfiles = [
        # train_speaker.RESULT_DIR + 'seq2seq_teacher_imagenet_%s_iter_5000.json',
        # train_speaker.RESULT_DIR + 'seq2seq_sample_imagenet_%s_iter_20000.json'
    ]
    for outfile in outfiles:
        for split in ['val_seen', 'val_unseen']:
            ev = SpeakerEvaluation([split])
            score_summary, _ = ev.score_file(outfile % split)
            print('\n%s' % outfile)
            pp.pprint(score_summary)

if __name__ == '__main__':
    from train import make_arg_parser
    #utils.run(make_arg_parser(), eval_simple_agents)
    #eval_seq2seq()