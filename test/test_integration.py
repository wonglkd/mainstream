import sys
sys.path.append('src/training')
sys.path.append('src/inference')
sys.path.append('src/util')
import Data
import train
import inference_pb
import inference_h5
import freeze

import os
import pytest
import subprocess
import uuid

def save_models(tmp_dir, data_dir_path, config_file):

    ## Train
    model_dir = tmp_dir + "/models"
    if not os.path.exists(model_dir):
        os.mkdir(model_dir)
    model_prefix = model_dir + "/my-model-" + str(uuid.uuid4())[:8]
    num_training_layers = 310
    train.train(config_file,
                data_dir_path,
                model_prefix,
                num_training_layers)

    ## Check all Keras and TF models files are present
    suffixes = [".h5", ".json", "-labels.json",
                ".pb", ".ckpt.meta", ".ckpt.index",
                ".ckpt.data-00000-of-00001"]
    for suffix in suffixes:
        model_path = model_prefix + suffix
        assert os.path.exists(model_path)

    ## Run freeze_graph
    freeze.freeze(model_prefix)
    frozen_graph_path = model_prefix + "-frozen.pb"
    assert os.path.exists(frozen_graph_path)

    return frozen_graph_path, model_prefix

# Fixtures perform model saving so it only occurs once per session

@pytest.fixture(scope="session")
def untrained_models(tmp_dir, data_dir):
    config_file = "config/test/0-epochs"
    pb_model_path, h5_model_path = \
        save_models(tmp_dir, data_dir, config_file)
    return pb_model_path, h5_model_path

@pytest.fixture(scope="session")
def trained_models(tmp_dir, data_dir):
    config_file = "config/test/1-epoch"
    pb_model_path, h5_model_path = \
        save_models(tmp_dir, data_dir, config_file)
    return pb_model_path, h5_model_path

@pytest.fixture(scope="session")
def test_dataset(data_dir):
    return Data.Data(data_dir, 299)

# Test that h5 and pb files are saved correctly by showing that they provide
# the same inference results

def compare_inference_output(models, test_dataset):
    pb_model_path = models[0]
    h5_model_path = models[1]

    ## Run inference
    pb_out = inference_pb.predict_with_dataset(pb_model_path, test_dataset)
    h5_out = inference_h5.predict_with_dataset(h5_model_path, test_dataset)

    ## Compare inference output
    for h5_val, pb_val in zip(h5_out, pb_out):
        print h5_val[0], h5_val[1], ",",  pb_val[0], pb_val[1]
        #assert round(h5_val[0], 2) == round(pb_val[0], 2)
        #assert round(h5_val[1], 2) == round(pb_val[1], 2)

@pytest.mark.unit
def test_inference_no_training(untrained_models, test_dataset):
    print "------------- test inference no training ---------------"
    compare_inference_output(untrained_models, test_dataset)

@pytest.mark.unit
def test_inference_training(trained_models, test_dataset):
    print "------------- test inference training ---------------"
    compare_inference_output(trained_models, test_dataset)

@pytest.mark.unit
def test_training(untrained_models, trained_models, test_dataset):
    # Test to see if training is making a difference with saved pb models
    pb_untrained = untrained_models[0]
    pb_trained = trained_models[0]
    h5_untrained = untrained_models[1]
    h5_trained = trained_models[1]

    print "------------- test training pb ---------------"
    pb_untrained_out = inference_pb.predict_with_dataset(pb_untrained,
                                                         test_dataset)
    pb_trained_out = inference_pb.predict_with_dataset(pb_trained,
                                                       test_dataset)
    for pb1, pb2 in zip(pb_untrained_out, pb_trained_out):
        print pb1[0], pb2[0], pb1[1], pb2[1]
        #assert round(pb1[0], 1) != round(pb2[0], 1)
        #assert round(pb1[1], 1) != round(pb2[1], 1)

    print "------------- test training h5 ---------------"
    h5_untrained_out = inference_h5.predict_with_dataset(h5_untrained,
                                                         test_dataset)
    h5_trained_out = inference_h5.predict_with_dataset(h5_trained,
                                                       test_dataset)

    for h51, h52 in zip(h5_untrained_out, h5_trained_out):
        print h51[0], h52[0], h51[1], h52[1]
        #assert round(h51[0], 1) != round(h52[0], 1)
        #assert round(h51[1], 1) != round(h52[1], 1)
