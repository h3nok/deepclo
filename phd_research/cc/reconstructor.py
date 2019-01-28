
import tensorflow as tf
from pprint import pprint
from map_measure import (Measure, MeasureType, Ordering, map_measure_fn,
                         MEASURE_MAP)
import itertools
import multiprocessing
from joblib import Parallel, delayed
import numpy as np


def _determine_measure_type(measure):
    assert isinstance(measure, Measure)
    if measure in [Measure.JE, Measure.MI, Measure.CE]:
        return MeasureType.Dist


def _swap(p1, p2):
    return p2, p1


def _print(patches):
    for key, value in patches.items():
        print("Current index: %i, Rank: %f" %
              (key, value))


def _sort_patches_by_distance_measure(patches_data, total_patches, measure=Measure.JE, ordering=Ordering.Ascending):
    """[summary]

    Arguments:
        patches_data {tensor} -- tensor having shape [number_of_patches, height,width,channel]
        total_patches {int} -- total number of patches 

    Keyword Arguments:
        measure {Measure} -- ranking measure to use for sorting (default: {Measure.JE})
        ordering {Ordering} -- sort order (default: {Ordering.Ascending})
    """
    # TODO - parallel implementation

    measure_type = _determine_measure_type(measure)

    assert measure_type == MeasureType.Dist, "Supplied measure is not distance measure, please call _sort_patches_by_standalone_measure instead"

    measure_fn = map_measure_fn(measure, measure_type)
    closest_patch_original_index = -1

    print("Number of patches: {}".format(total_patches))

    def _compare_numpy(reference_patch, patch):
        patches_to_compare = (reference_patch, patch)
        distance = measure_fn(patches_to_compare)
        return distance

    sess = tf.get_default_session()
    patches_data = sess.run(patches_data)

    def _swap(i, j):
        patches_data[[i, j]] = patches_data[[j, i]]

    sorted_patches = []
    debug_sorted_patches = dict()
    distance = -100
    reference_patch_data = patches_data[0]

    _swap(0,1)

    for i in range(0, total_patches):
        # TODO- make configurable
        closest_distance = 100  # determine ordering
        sorted_patches.append(reference_patch_data)
        debug_sorted_patches[i] = distance
        print("Closeses so far: %f" % closest_distance)
        for j in range(i+1, total_patches):
            distance = _compare_numpy(reference_patch_data, patches_data[j])
            print("\tDistance between %d and %d = %f" % (i, j, distance))
            if distance < closest_distance:
                print("Found smaller: %f < %f" % (distance, closest_distance))
                closest_patch_original_index = j
                closest_distance = distance
                reference_patch_data = patches_data[j]

        # print("=====>> Closest at j %d, distance = %f" %
            #   (closest_patch_original_index, closest_distance))
    print(len(sorted_patches))
    _print(debug_sorted_patches)


def _sort_patches_by_content_measure():
    pass


def reconstruct_from_patches(patches, image_h, image_w, measure=Measure.JE):
    """
    Reconstructs an image from patches of size patch_h x patch_w
    Input: batch of patches shape [n, patch_h, patch_w, patch_ch]
    Output: image of shape [image_h, image_w, patch_ch]

    Arguments:
        patches {tftensor} -- a list of patches of a given image in tftensor or numpy.array format 
        image_h {int} -- image width 
        image_w {int} -- image height 

    Keyword Arguments:
        measure {Measure} -- measure to use to sort patches (default: {None})
    """
    assert patches.shape.ndims == 4, "Patches tensor must be of shape [total_patches, p_w,p_h,c]"

    number_of_patches = patches.shape[0]
    _sort_patches_by_distance_measure(patches, number_of_patches, measure)

    pad = [[0, 0], [0, 0]]
    patch_h = patches.shape[1].value
    patch_w = patches.shape[2].value
    patch_ch = patches.shape[3].value
    p_area = patch_h * patch_w
    h_ratio = image_h // patch_h
    w_ratio = image_w // patch_w

    image = tf.reshape(patches, [1, h_ratio, w_ratio, p_area, patch_ch])
    image = tf.split(image, p_area, 3)
    image = tf.stack(image, 0)
    image = tf.reshape(image, [p_area, h_ratio, w_ratio, patch_ch])
    image = tf.batch_to_space_nd(image, [patch_h, patch_w], pad)

    return image[0]
