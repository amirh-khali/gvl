import argparse
import time
import yaml
import os
import numpy as np

def parse_opts():
    parser = argparse.ArgumentParser()

    # configure of this run
    parser.add_argument('--cfg_path', type=str, required=True, help='config file')
    parser.add_argument('--id', type=str, default='', help='id of this run. Results and logs will saved in this folder ./save/id')
    parser.add_argument('--fixid', type=str, default='', help='this parameter is not used in current version')
    parser.add_argument('--gpu_id', type=str, nargs='+', default=[])
    parser.add_argument('--disable_tqdm', action='store_true')
    parser.add_argument('--seed', type=int, default=777)
    parser.add_argument('--random_seed',  action='store_true', help='choose a random seed from {1,...,1000}')
    parser.add_argument('--disable_cudnn', type=int, default=0, help='disable cudnn may solve some unknown bugs')
    parser.add_argument('--debug', action='store_true', help='using mini-dataset for fast debugging')
    parser.add_argument('--device', default='cuda', choices=['cpu', 'cuda'], help='device to use for training / testing')
    parser.add_argument('--train_use_amp', action='store_true', default=False)

    #  ***************************** INPUT DATA PATH *****************************
    parser.add_argument('--train_caption_file', type=str,
                        default='data/anet/captiondata/train_modified.json', help='')
    parser.add_argument('--invalid_video_json', type=str, nargs='+', default=[])
    parser.add_argument('--val_caption_file', type=str, default='data/anet/captiondata/val_1.json')
    parser.add_argument('--visual_feature_folder', type=str, default='data/anet/resnet_bn')
    parser.add_argument('--gt_file_for_auc', type=str, nargs='+', default='data/anet/captiondata/val_all.json')
    parser.add_argument('--gt_file_for_eval', type=str, nargs='+', default=['data/anet/captiondata/val_1.json', 'data/anet/captiondata/val_2.json'])
    parser.add_argument('--gt_file_for_para_eval', type=str, nargs='+', default= ['data/anet/captiondata/para/anet_entities_val_1_para.json', 'data/anet/captiondata/para/anet_entities_val_2_para.json'])
    parser.add_argument('--dict_file', type=str, default='data/anet/vocabulary_activitynet.json', help='')
    parser.add_argument('--criteria_for_best_ckpt', type=str, default='dvc', choices=['dvc', 'pc', 'grounding'], help='for dense video captioning, use soda_c + METEOR as the criteria'
                                                                                                         'for paragraph captioning, choose the best para_METEOR+para_CIDEr+para_BLEU4'
                                                                                                         'for temporal visual grounding, choose the best IOU0.3 + IOU0.5 + IOU0.7')
    parser.add_argument('--visual_feature_type', type=str, default='c3d', choices=['c3d', 'resnet_bn', 'resnet'])
    parser.add_argument('--feature_dim', type=int, default=500, help='dim of frame-level feature vector')

    parser.add_argument('--start_from', type=str, default='', help='id of the run with incompleted training')
    parser.add_argument('--start_from_mode', type=str, choices=['best', 'last'], default="last")
    parser.add_argument('--pretrain', type=str, choices=['full', 'encoder', 'decoder'])
    parser.add_argument('--pretrain_path', type=str, default='', help='path of .pth')

    #  ***************************** DATALOADER OPTION *****************************
    parser.add_argument('--nthreads', type=int, default=4)
    parser.add_argument('--data_norm', type=int, default=0)
    parser.add_argument('--data_rescale', type=int, default=1)

    parser.add_argument('--feature_sample_rate', type=int, default=1)
    parser.add_argument('--train_proposal_sample_num', type=int,
                        default=24,
                        help='number of sampled proposals (or proposal sequence), a bigger value may be better')
    parser.add_argument('--gt_proposal_sample_num', type=int, default=10)


    #  ***************************** Caption Decoder  *****************************
    parser.add_argument('--vocab_size', type=int, default=5747)
    parser.add_argument('--wordRNN_input_feats_type', type=str, default='C', choices=['C', 'E', 'C+E'],
                        help='C:clip-level features, E: event-level features, C+E: both')
    parser.add_argument('--caption_decoder_type', type=str, default="light",
                        choices=['none','light', 'standard'])
    parser.add_argument('--enable_pos_emb_for_captioner', action='store_true', default=False) ## added by 0_wt on 2022/03/01
    parser.add_argument('--rnn_size', type=int, default=512,
                        help='size of the rnn in number of hidden nodes in each layer')
    parser.add_argument('--num_layers', type=int, default=1, help='number of layers in the RNN')
    parser.add_argument('--input_encoding_size', type=int, default=512,
                        help='the encoding size of each token in the vocabulary')
    parser.add_argument('--att_hid_size', type=int, default=512, help='the hidden size of the attention MLP')
    parser.add_argument('--drop_prob', type=float, default=0.5, help='strength of dropout in the Language Model RNN')
    parser.add_argument('--max_caption_len', type=int, default=30, help='')

    #  ***************************** Transformer  *****************************
    parser.add_argument('--hidden_dim', type=int, default=512)
    parser.add_argument('--num_queries', type=int, default=100)
    parser.add_argument('--hidden_dropout_prob', type=float, default=0.5)
    parser.add_argument('--layer_norm_eps', type=float, default=1e-12)
    parser.add_argument('--caption_cost_type', type=str, default='loss')
    parser.add_argument('--caption_loss_type', type=str, default='ce')
    parser.add_argument('--set_cost_caption', type=float, default=0)
    parser.add_argument('--set_cost_class', type=float, default=1)
    parser.add_argument('--set_cost_bbox', type=float, default=5)
    parser.add_argument('--set_cost_giou', type=float, default=2)
    parser.add_argument('--cost_alpha', type=float, default=0.25)
    parser.add_argument('--cost_gamma', type=float, default=2)

    parser.add_argument('--bbox_loss_coef', default=5, type=float)
    parser.add_argument('--giou_loss_coef', default=2, type=float)
    parser.add_argument('--count_loss_coef', default=0, type=float)
    parser.add_argument('--caption_loss_coef', default=0, type=float)
    parser.add_argument('--eos_coef', default=0.1, type=float,
                        help="Relative classification weight of the no-object class")
    parser.add_argument('--num_classes', type=int, default=1)
    parser.add_argument('--dec_layers', type=int, default=6)
    parser.add_argument('--enc_layers', type=int, default=6)
    parser.add_argument('--transformer_ff_dim', type=int, default=2048)
    parser.add_argument('--transformer_dropout_prob', type=float, default=0.1)
    parser.add_argument('--frame_embedding_num', type=int, default = 100)
    parser.add_argument('--sample_method', type=str, default = 'nearest', choices=['nearest', 'linear'])
    parser.add_argument('--fix_xcw', type=int, default=0)
    parser.add_argument('--box_head_init_bias', type=float, default=-2.0)


    #  ***************************** OPTIMIZER *****************************
    parser.add_argument('--training_scheme', type=str, default='all', choices=['cap_head_only', 'no_cap_head', 'all'])
    parser.add_argument('--epoch', type=int, default=30)
    parser.add_argument('--batch_size', type=int, default=1, help='batch_size')
    parser.add_argument('--eval_batch_size', type=int, default=1, help='')
    parser.add_argument('--grad_clip', type=float, default=100., help='clip gradients at this value')
    parser.add_argument('--optimizer_type', type=str, default='adam')
    parser.add_argument('--weight_decay', type=float, default=0, help='weight_decay')

    parser.add_argument('--lr', type=float, default=1e-4, help='1e-4 for resnet feature and 5e-5 for C3D feature')
    parser.add_argument('--task_heads_lr', type=float, default=5e-5)
    parser.add_argument('--task_heads_different_lr', action='store_true')
    parser.add_argument('--learning_rate_decay_start', type=float, default=8)
    parser.add_argument('--learning_rate_decay_every', type=float, default=3)
    parser.add_argument('--learning_rate_decay_rate', type=float, default=0.5)

    #  ***************************** SAVING AND LOGGING *****************************
    parser.add_argument('--min_epoch_when_save', type=int, default=-1)
    parser.add_argument('--save_checkpoint_every', type=int, default=1)
    parser.add_argument('--save_all_checkpoint', action='store_true')
    parser.add_argument('--save_dir', type=str, default='save', help='directory to store checkpointed models')

    #  ***************************** For Deformable DETR *************************************
    parser.add_argument('--lr_backbone_names', default=["None"], type=str, nargs='+')
    parser.add_argument('--lr_backbone', default=2e-5, type=float)
    parser.add_argument('--lr_proj', default=0, type=int)

    parser.add_argument('--learning_strategy', type=str, default='multi_step',choices=('warmup_linear', 'multi_step', 'warmup_cosine'))
    parser.add_argument('--warm_up_ratio', type=float, default=0.1, help='Fraction of total number of steps')

    parser.add_argument('--lr_linear_proj_names', default=['reference_points', 'sampling_offsets'], type=str, nargs='+')
    parser.add_argument('--lr_linear_proj_mult', default=0.1, type=float)

    # Variants of Deformable DETR
    parser.add_argument('--with_box_refine', default=False, action='store_true')
    parser.add_argument('--transformer_input_type', default='queries', choices=['gt_proposals', 'learnt_proposals', 'queries'])

    # * Backbone
    parser.add_argument('--backbone', default=None, type=str,
                        help="Name of the convolutional backbone to use")
    parser.add_argument('--dilation', action='store_true',
                        help="If true, we replace stride with dilation in the last convolutional block (DC5)")
    parser.add_argument('--position_embedding', default='sine', type=str, choices=('sine', 'learned'),
                        help="Type of positional embedding to use on top of the image features")
    parser.add_argument('--position_embedding_scale', default=2 * np.pi, type=float,
                        help="position / size * scale")
    parser.add_argument('--num_feature_levels', default=4, type=int, help='number of feature levels')

    # * Transformer

    parser.add_argument('--nheads', default=8, type=int,
                        help="Number of attention heads inside the transformer's attentions")
    parser.add_argument('--dec_n_points', default=4, type=int)
    parser.add_argument('--enc_n_points', default=4, type=int)

    parser.add_argument('--share_caption_head', type = int ,default=1)

    parser.add_argument('--cap_nheads', default=8, type=int)
    parser.add_argument('--cap_dec_n_points', default=4, type=int)
    parser.add_argument('--cap_num_feature_levels', default=4, type=int)
    parser.add_argument('--disable_mid_caption_heads', action='store_true')

    # Loss
    parser.add_argument('--no_aux_loss', dest='aux_loss', action='store_false',
                        help="Disables auxiliary decoding losses (loss at each layer)")


    # * Loss coefficients
    parser.add_argument('--cls_loss_coef', default=2, type=float)
    parser.add_argument('--focal_alpha', default=0.25, type=float)
    parser.add_argument('--focal_gamma', default=2., type=float)

    # Pretrain weight:
    parser.add_argument('--remove_class_head_weight', action='store_true')
    parser.add_argument('--remove_bbox_head_weight', action='store_true')
    parser.add_argument('--remove_caption_head_weight', action='store_true')
    parser.add_argument('--remove_contrastive_projection_weight', action='store_true')


    #***************************** Event counter *****************************
    parser.add_argument('--max_eseq_length', default=10, type=int)
    parser.add_argument('--lloss_gau_mask', default=1, type=int)
    parser.add_argument('--lloss_beta', default=1, type=float)

    #  ***************************** Scheduled Sampling *****************************
    parser.add_argument('--scheduled_sampling_start', type=int, default=-1,
                        help='at what iteration to start decay gt probability')
    parser.add_argument('--basic_ss_prob', type=float, default=0, help='initial ss prob')
    parser.add_argument('--scheduled_sampling_increase_every', type=int, default=2,
                        help='every how many iterations thereafter to gt probability')
    parser.add_argument('--scheduled_sampling_increase_prob', type=float, default=0.05,
                        help='How much to update the prob')
    parser.add_argument('--scheduled_sampling_max_prob', type=float, default=0.25,
                        help='Maximum scheduled sampling prob.')

    parser.add_argument('--dataset', type=str, default='anet')


    #  ***************************** Text Encoder *****************************
    parser.add_argument('--pretrained_language_model', type=str, default='roberta-base',    help='Pretrained hugging face model')
    parser.add_argument('--load_pretrained_language_model_from_config', type=str, default=None, help='creating a randomly initialized model')
    parser.add_argument('--gpt_model', type=str, default='gpt2')
    parser.add_argument('--text_encoder_lr', type=float, default=1e-5, help='Learning rate of text encoder')
    parser.add_argument('--text_encoder_learning_strategy', type=str, default='warmup_linear',choices=('warmup_linear', 'multi_step', 'frozen', 'warmup_cosine'))
    parser.add_argument('--text_encoder_warm_up_ratio', type=float, default=0.01, help='Fraction of total number of steps')
    parser.add_argument('--text_encoder_lr_decay_start', type=float, default=8)
    parser.add_argument('--text_encoder_lr_decay_every', type=float, default=3)
    parser.add_argument('--text_encoder_lr_decay_rate', type=float, default=0.5)
    parser.add_argument('--max_text_input_len', type=int, default=32, help='')
    parser.add_argument('--enable_layer_diff_text_feature', type=bool, default=False,help='Aux layer will have different text feature from final layer if true')
    parser.add_argument('--enable_word_context_modeling', type=bool, default=False, help='')
    parser.add_argument('--word_context_modeling_type',  type=str, default='attention_pool')
    parser.add_argument('--enable_sentence_context_modeling', type=bool, default=False, help='If add extra self attention layer after text encoder')
    parser.add_argument('--enable_sentence_pos_embedding', type=bool, default=False)
    parser.add_argument('--sentence_pos_embedding_type', type=str, default='cosine')
    parser.add_argument('--enable_multilayer_projection', default=False)
    parser.add_argument('--max_pos_num', type=int, default=500)
    parser.add_argument('--sentence_modeling_layer_num', type=int, default=1)

    parser.add_argument('--enable_cross_model_fusion', type=bool, default=False)
    # proposal level attention loss
    parser.add_argument('--huggingface_cache_dir', type=str, default='.cache')

    #  ***************************** Contrastive Loss  *****************************
    parser.add_argument('--enable_contrastive', action='store_true', help='whether to use query-text contrastive loss')
    parser.add_argument('--contrastive_hidden_size', type=int, default=128, help='Contrastive hidden size')
    parser.add_argument('--contrastive_loss_start_coef', type=float, default=0.0, help='Weight of contrastive loss')
    parser.add_argument('--contrastive_loss_temperature', type=float, default=0.1, help='Temperature of cl temperature')
    parser.add_argument('--enable_cross_video_cl', type=bool, default=True, help='Enable cross video contrastive loss')
    parser.add_argument('--set_cost_cl', type=float, default=0.0)
    parser.add_argument('--cl_schedule_val', type=float, nargs='+', default=[0, 0.1])
    parser.add_argument('--cl_schedule_time', type=int, nargs='+', default=[0, 2])
    parser.add_argument('--disable_cl_proj_layer_share_weight', action='store_true', help='use unshared weights for cl project layers')
    parser.add_argument('--enable_e2t_cl', action='store_true', help=' enable event-to-text contrastive')
    parser.add_argument('--enable_bg_for_cl', action='store_true', help=' add a class for background events')

    # finetuning captioner
    parser.add_argument('--only_ft_captioner', action='store_true', help='finetuning caption head needs loading pretrained weights')
    parser.add_argument('--ft_captioner_from_scratch', action='store_true', help='finetuning caption head without loading captioner weights')

    # finetune class caption head
    parser.add_argument('--only_ft_class_head', action='store_true', help='Linear probing for action detection')
    parser.add_argument('--action_classes_path', type=str, default='data/anet/anet1.3/action_name.txt')
    parser.add_argument('--tal_gt_file', type=str, default='data/anet/anet1.3/activity_net.v1-3.min.json')
    parser.add_argument('--support_mlp_class_head', action='store_true')

    # For grounding
    parser.add_argument('--eval_enable_grounding', default=True)
    parser.add_argument('--eval_enable_maximum_matching_for_grounding', default=False)
    parser.add_argument('--eval_set_cost_class', type=float, default=0.)
    parser.add_argument('--eval_grounding_cost_alpha', type=float, default=0.25)
    parser.add_argument('--eval_grounding_cost_gamma', type=float, default=2)
    parser.add_argument('--eval_set_cost_cl', type=float, default=1.0)
    parser.add_argument('--eval_disable_captioning', action='store_true', default=False)
    parser.add_argument('--eval_disable_contrastive', action='store_true', default=False)
    parser.add_argument('--eval_enable_matching_score', action='store_true', default=False)
    parser.add_argument('--eval_matching_score_weight', type=float, default=0.0)
    parser.add_argument('--eval_gt_file_for_grounding', type=str, default='data/anet/captiondata/grounding/val1_for_grounding.json')

    # Multi sentence grounding
    parser.add_argument('--train_with_split_anno', type=bool, default=False)

    # For fast evaluation
    parser.add_argument('--eval_tool_version', type=str, default='2018', choices=['2018', '2021', '2018_cider'])
    
    # video cropping
    parser.add_argument('--enable_video_cropping', action='store_true', default=False)
    parser.add_argument('--min_crop_ratio', type=float, default=0.5)
    parser.add_argument('--crop_num', type=int, default=2)

    # reranking
    parser.add_argument('--ec_alpha', type=float, default=0.3)

    # GPT2 decode
    parser.add_argument('--prefix_num_mapping_layer', type=int, default=8)
    parser.add_argument('--prefix_size', type=int, default=512)
    parser.add_argument('--prefix_length', type=int, default=10)
    parser.add_argument('--eval_use_amp', action='store_true', default=False)

    # RL
    parser.add_argument('--rl_scorer_types', type=str, nargs='+', default=['Meteor'], choices=['Meteor', 'CiderD'])
    parser.add_argument('--rl_scorer_weights', type=float, nargs='+', default=[1.])
    parser.add_argument('--cached_tokens', type=str, default='anet/activitynet_train_ngrams_for_cider-idxs')
    parser.add_argument('--cl_para_ratio', type=float, default=0.0)
    parser.add_argument('--cl_sent_ratio', type=float, default=1.0)
    

    args = parser.parse_args()


    if args.cfg_path:
        import_cfg(args.cfg_path, vars(args))

    if args.random_seed:
        import random
        seed = int(random.random() * 1000)
        new_id = args.id + '_seed{}'.format(seed)
        save_folder = os.path.join(args.save_dir, new_id)
        while os.path.exists(save_folder):
            seed = int(random.random() * 1000)
            new_id = args.id + '_seed{}'.format(seed)
            save_folder = os.path.join(args.save_dir, new_id)
        args.id = new_id
        args.seed = seed

    if args.debug:
        args.id = 'debug_' + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        args.save_checkpoint_every = 1
        args.shuffle = 0

    if args.caption_decoder_type == 'none':
        assert args.caption_loss_coef == 0
        assert args.set_cost_caption == 0

    print("args.id: {}".format(args.id))
    export_to_json(args)
    return args

def import_cfg(cfg_path, args):
    with open(cfg_path, 'r') as handle:
        yml = yaml.load(handle, Loader=yaml.FullLoader)
        if 'base_cfg_path' in yml:
            base_cfg_path = yml['base_cfg_path']
            import_cfg(base_cfg_path, args)
        args.update(yml)
    pass

def export_to_json(args):
    # save a copy of all args in the lastest version,
    # used to recover the missing args when evaluating old runs by eval.py
    import json
    if not os.path.exists('.tmp'):
        os.mkdir('.tmp')
    json.dump(vars(args), open(".tmp/opts.json", 'w'))

if __name__ == '__main__':
    opt = parse_opts()
    export_to_json(opt)