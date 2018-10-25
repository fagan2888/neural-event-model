'''
Keras is great, but it makes certain assumptions that do not quite work for NLP problems. We override some of those
assumptions here.
'''
from overrides import overrides

from keras import backend as K
from keras.layers import Embedding, TimeDistributed, Flatten


class AnyShapeEmbedding(Embedding):
    '''
    We just want Embedding to work with inputs of any number of dimensions.
    This can be accomplished by simply changing the output shape computation.
    '''
    @overrides
    def get_output_shape_for(self, input_shape):
        return input_shape + (self.output_dim,)


class TimeDistributedRNN(TimeDistributed):
    '''
    The TimeDistributed wrapper in Keras works for recurrent layers as well, except that it does not handle masking
    correctly. In case when the wrapper recurrent layer does not return a sequence, no mask is returned. However,
    when we are time distributing it, it is possible that some sequences are entirely padding, for example, when
    one of the slots being encoded is not present in the input at all. We override masking here.
    '''
    @overrides
    def compute_mask(self, x, input_mask=None):
        # pylint: disable=unused-argument
        if input_mask is None:
            return None
        else:
            return K.any(input_mask, axis=-1)


class MaskedFlatten(Flatten):
    '''
    Flatten does not allow masked inputs. This class does.
    '''
    def __init__(self, **kwargs):
        super(MaskedFlatten, self).__init__(**kwargs)
        self.supports_masking = True

    def call(self, inputs, mask=None):
        # Assuming the output will be passed through a dense layer after this.
        if mask is not None:
            inputs = switch(K.expand_dims(mask), inputs, K.zeros_like(inputs))
        return super(MaskedFlatten, self).call(inputs)

    def compute_mask(self, inputs, mask=None):
        return None


def switch(cond, then_tensor, else_tensor):
    '''
    Keras' implementation of switch for tensorflow works differently compared to that for theano. This function
    selects the appropriate methods.
    '''
    if K.backend() == 'tensorflow':
        import tensorflow as tf
        cond_shape = cond.get_shape()
        input_shape = then_tensor.get_shape()
        if cond_shape[-1] != input_shape[-1] and cond_shape[-1] == 1:
            # This means the last dim is an embedding dimension.
            cond = K.dot(tf.cast(cond, tf.float32), tf.ones((1, input_shape[-1])))
        return tf.where(tf.cast(cond, dtype=tf.bool), then_tensor, else_tensor)
    else:
        import theano.tensor as T
        return T.switch(cond, then_tensor, else_tensor)
