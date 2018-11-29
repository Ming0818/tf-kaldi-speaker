import tensorflow as tf
from model.pooling import statistics_pooling
from collections import OrderedDict


def tdnn(features, params, is_training=None, reuse_variables=None):
    """Build a TDNN network.

    Args:
        features: A tensor with shape [batch, length, dim].
        params: Configuration loaded from a JSON.
        is_training: True if the network is used for training.
        reuse_variables: True if the network has been built and enable variable reuse.

    :return:
        features: The output of the last layer.
        endpoints: An OrderedDict containing output of every components. The outputs are in the order that they add to
                   the network. Thus it is convenient to split the network by a output name
    """
    endpoints = OrderedDict()
    with tf.variable_scope("tdnn", reuse=reuse_variables):
        # Convert to [b, 1, l, d]
        features = tf.expand_dims(features, 1)

        # Layer 1: [-2,-1,0,1,2] --> [b, 1, l-4, 512]
        # conv2d + batchnorm + relu
        features = tf.layers.conv2d(features,
                                512,
                                (1, 5),
                                activation=None,
                                kernel_regularizer=tf.contrib.layers.l2_regularizer(params.weight_l2_regularizer),
                                name='tdnn1_conv')
        endpoints["tdnn1_conv"] = features
        features = tf.layers.batch_normalization(features,
                                                 momentum=params.batchnorm_momentum,
                                                 training=is_training,
                                                 name="tdnn1_bn")
        endpoints["tdnn1_bn"] = features
        features = tf.nn.relu(features, name='tdnn1_relu')
        endpoints["tdnn1_relu"] = features

        # Layer 2: [-2, -1, 0, 1, 2] --> [b ,1, l-4, 512]
        # conv2d + batchnorm + relu
        # This is slightly different with Kaldi which use dilation convolution
        features = tf.layers.conv2d(features,
                                    512,
                                    (1, 5),
                                    activation=None,
                                    kernel_regularizer=tf.contrib.layers.l2_regularizer(params.weight_l2_regularizer),
                                    name='tdnn2_conv')
        endpoints["tdnn2_conv"] = features
        features = tf.layers.batch_normalization(features,
                                                 momentum=params.batchnorm_momentum,
                                                 training=is_training,
                                                 name="tdnn2_bn")
        endpoints["tdnn2_bn"] = features
        features = tf.nn.relu(features, name='tdnn2_relu')
        endpoints["tdnn2_relu"] = features

        # Layer 3: [-3, -2, -1, 0, 1, 2, 3] --> [b, 1, l-6, 512]
        # conv2d + batchnorm + relu
        # Still, use a non-dilation one
        features = tf.layers.conv2d(features,
                                    512,
                                    (1, 7),
                                    activation=None,
                                    kernel_regularizer=tf.contrib.layers.l2_regularizer(params.weight_l2_regularizer),
                                    name='tdnn3_conv')
        endpoints["tdnn3_conv"] = features
        features = tf.layers.batch_normalization(features,
                                                 momentum=params.batchnorm_momentum,
                                                 training=is_training,
                                                 name="tdnn3_bn")
        endpoints["tdnn3_bn"] = features
        features = tf.nn.relu(features, name='tdnn3_relu')
        endpoints["tdnn3_relu"] = features

        # Convert to [b, l, 512]
        features = tf.squeeze(features, axis=1)

        # Layer 4: [b, l, 512] --> [b, l, 512]
        features = tf.layers.dense(features,
                                   512,
                                   activation=None,
                                   kernel_regularizer=tf.contrib.layers.l2_regularizer(params.weight_l2_regularizer),
                                   name="tdnn4_dense")
        endpoints["tdnn4_dense"] = features
        features = tf.layers.batch_normalization(features,
                                                 momentum=params.batchnorm_momentum,
                                                 training=is_training,
                                                 name="tdnn4_bn")
        endpoints["tdnn4_bn"] = features
        features = tf.nn.relu(features, name='tdnn4_relu')
        endpoints["tdnn4_relu"] = features

        # Layer 5: [b, l, x]
        if "num_nodes_pooling_layer" not in params.dict:
            # The default number of nodes before pooling
            params.dict["num_nodes_pooling_layer"] = 1500

        features = tf.layers.dense(features,
                                   params.num_nodes_pooling_layer,
                                   activation=None,
                                   kernel_regularizer=tf.contrib.layers.l2_regularizer(params.weight_l2_regularizer),
                                   name="tdnn5_dense")
        endpoints["tdnn5_dense"] = features
        features = tf.layers.batch_normalization(features,
                                                 momentum=params.batchnorm_momentum,
                                                 training=is_training,
                                                 name="tdnn5_bn")
        endpoints["tdnn5_bn"] = features
        features = tf.nn.relu(features, name='tdnn5_relu')
        endpoints["tdnn5_relu"] = features

        # Statistics pooling
        # [b, l, 1500] --> [b, 1500]
        if params.pooling_type == "statistics_pooling":
            features = statistics_pooling(features)
        else:
            raise NotImplementedError("Not implement %s pooling" % params.poolingtype)
        endpoints['pooling'] = features

        # Utterance-level network
        # Layer 6: [b, 512]
        features = tf.layers.dense(features,
                                   512,
                                   activation=None,
                                   kernel_regularizer=tf.contrib.layers.l2_regularizer(params.weight_l2_regularizer),
                                   name='tdnn6_dense')
        endpoints['tdnn6_dense'] = features
        features = tf.layers.batch_normalization(features,
                                                 momentum=params.batchnorm_momentum,
                                                 training=is_training,
                                                 name="tdnn6_bn")
        endpoints["tdnn6_bn"] = features
        features = tf.nn.relu(features, name='tdnn6_relu')
        endpoints["tdnn6_relu"] = features

        # Layer 7: [b, x]
        if "num_nodes_last_layer" not in params.dict:
            # The default number of nodes in the last layer
            params.dict["num_nodes_last_layer"] = 512
        features = tf.layers.dense(features,
                                   params.num_nodes_last_layer,
                                   activation=None,
                                   kernel_regularizer=tf.contrib.layers.l2_regularizer(params.weight_l2_regularizer),
                                   name='tdnn7_dense')
        endpoints['tdnn7_dense'] = features

        if not params.last_layer_linear:
            # If the last layer is linear, no further activation is needed.
            features = tf.layers.batch_normalization(features,
                                                     momentum=params.batchnorm_momentum,
                                                     training=is_training,
                                                     name="tdnn7_bn")
            endpoints["tdnn7_bn"] = features
            features = tf.nn.relu(features, name='tdnn7_relu')
            endpoints["tdnn7_relu"] = features

    return features, endpoints


if __name__ == "__main__":
    num_labels = 10
    num_data = 100
    num_length = 100
    num_dim = 100
    features = tf.placeholder(tf.float32, shape=[None, None, num_dim], name="features")
    labels = tf.placeholder(tf.int32, shape=[None], name="labels")
    embeddings = tf.placeholder(tf.float32, shape=[None, num_dim], name="embeddings")

    from misc.utils import ParamsPlain
    params = ParamsPlain()
    params.dict["weight_l2_regularizer"] = 1e-5
    params.dict["batchnorm_momentum"] = 0.999
    params.dict["pooling_type"] = "statistics_pooling"
    params.dict["last_layer_linear"] = False

    # tdnn + softmax
    outputs, endpoints = tdnn(features, params, is_training=True, reuse_variables=False)
    from model.loss import softmax
    loss = softmax(outputs, labels, 10, params, is_training=True, reuse_variables=False)
    grads = tf.gradients(loss, features)

    import numpy as np
    features_val = np.random.rand(num_data, num_length, num_dim).astype(np.float32)
    labels_val = np.random.randint(0, num_labels, size=(num_data,)).astype(np.int32)

    # The sqrt in the pooling is a dangerous operation, things may go wrong when the variance is zero. Test it
    features_val[-1, :, :] = 0

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        endpoints_val, grad_val = sess.run([endpoints, grads], feed_dict={features: features_val,
                                                                          labels: labels_val})
        assert not np.any(np.isnan(grad_val)), "Gradient should not be nan"
        before_pooling = endpoints_val["tdnn5_relu"]
        after_pooling = endpoints_val["pooling"]
        m = np.mean(before_pooling, axis=1)
        std = np.std(before_pooling, axis=1)
        p = np.concatenate((m, std), axis=1)
        assert np.allclose(after_pooling, p)

    # generalized end2end loss
    from model.loss import ge2e
    num_speakers = 64
    num_segments_per_speaker = 10
    num_data = num_speakers * num_segments_per_speaker
    params.dict["num_speakers_per_batch"] = num_speakers
    params.dict["num_segments_per_speaker"] = num_segments_per_speaker
    params.dict["init_end2end_w"] = 10
    params.dict["init_end2end_b"] = -5
    reuse_variables = False
    for ge2e_type in ["softmax", "contrastive"]:
        params.dict["ge2e_loss_type"] = ge2e_type
        loss = ge2e(embeddings, labels, 10, params, is_training=True, reuse_variables=reuse_variables)
        reuse_variables = True
        grads = tf.gradients(loss, embeddings)
        embeddings_val = np.random.rand(num_data, num_dim).astype(np.float32)
        labels_val = np.zeros(num_data, dtype=np.int32)
        for i in range(num_speakers):
            labels_val[i*num_segments_per_speaker:(i+1)*num_segments_per_speaker] = i

        from model.test_utils import compute_ge2e_loss
        loss_np = compute_ge2e_loss(embeddings_val, labels_val, params.init_end2end_w, params.init_end2end_b, params.ge2e_loss_type)

        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())
            loss_val, grad_val = sess.run([loss, grads], feed_dict={embeddings: embeddings_val,
                                                                    labels: labels_val})
            assert not np.any(np.isnan(grad_val)), "Gradient should not be nan"
            assert np.allclose(loss_val, loss_np)
