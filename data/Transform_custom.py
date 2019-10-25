import cv2
import numpy as np
from PIL import Image
import random
import math
from torchvision.transforms import Lambda
import torch
from skimage.util import random_noise
import torch.tensor


class RandomRotateCrop():
    """ Rotate the image and crop the black border out """

    def __init__(self, probability):
        self.probability = probability

    def rotate_image(self, image, angle):
        """
        Rotates an OpenCV 2 / NumPy image about it's centre by the given angle
        (in degrees). The returned image will be large enough to hold the entire
        new image, with a black background
        """

        # Get the image size
        # No that's not an error - NumPy stores image matricies backwards
        image_size = (image.shape[1], image.shape[0])
        image_center = tuple(np.array(image_size) / 2)

        # Convert the OpenCV 3x2 rotation matrix to 3x3
        rot_mat = np.vstack(
            [cv2.getRotationMatrix2D(image_center, angle, 1.0), [0, 0, 1]]
        )

        rot_mat_notranslate = np.matrix(rot_mat[0:2, 0:2])

        # Shorthand for below calcs
        image_w2 = image_size[0] * 0.5
        image_h2 = image_size[1] * 0.5

        # Obtain the rotated coordinates of the image corners
        rotated_coords = [
            (np.array([-image_w2,  image_h2]) * rot_mat_notranslate).A[0],
            (np.array([ image_w2,  image_h2]) * rot_mat_notranslate).A[0],
            (np.array([-image_w2, -image_h2]) * rot_mat_notranslate).A[0],
            (np.array([ image_w2, -image_h2]) * rot_mat_notranslate).A[0]
        ]

        # Find the size of the new image
        x_coords = [pt[0] for pt in rotated_coords]
        x_pos = [x for x in x_coords if x > 0]
        x_neg = [x for x in x_coords if x < 0]

        y_coords = [pt[1] for pt in rotated_coords]
        y_pos = [y for y in y_coords if y > 0]
        y_neg = [y for y in y_coords if y < 0]

        right_bound = max(x_pos)
        left_bound = min(x_neg)
        top_bound = max(y_pos)
        bot_bound = min(y_neg)

        new_w = int(abs(right_bound - left_bound))
        new_h = int(abs(top_bound - bot_bound))

        # We require a translation matrix to keep the image centred
        trans_mat = np.matrix([
            [1, 0, int(new_w * 0.5 - image_w2)],
            [0, 1, int(new_h * 0.5 - image_h2)],
            [0, 0, 1]
        ])

        # Compute the tranform for the combined rotation and translation
        affine_mat = (np.matrix(trans_mat) * np.matrix(rot_mat))[0:2, :]

        # Apply the transform
        result = cv2.warpAffine(
            image,
            affine_mat,
            (new_w, new_h),
            flags=cv2.INTER_LINEAR
        )

        return result


    def largest_rotated_rect(self, w, h, angle):
        """
        Given a rectangle of size wxh that has been rotated by 'angle' (in
        radians), computes the width and height of the largest possible
        axis-aligned rectangle within the rotated rectangle.

        Original JS code by 'Andri' and Magnus Hoff from Stack Overflow

        Converted to Python by Aaron Snoswell
        """

        quadrant = int(math.floor(angle / (math.pi / 2))) & 3
        sign_alpha = angle if ((quadrant & 1) == 0) else math.pi - angle
        alpha = (sign_alpha % math.pi + math.pi) % math.pi

        bb_w = w * math.cos(alpha) + h * math.sin(alpha)
        bb_h = w * math.sin(alpha) + h * math.cos(alpha)

        gamma = math.atan2(bb_w, bb_w) if (w < h) else math.atan2(bb_w, bb_w)

        delta = math.pi - alpha - gamma

        length = h if (w < h) else w

        d = length * math.cos(alpha)
        a = d * math.sin(alpha) / math.sin(delta)

        y = a * math.cos(gamma)
        x = y * math.tan(gamma)

        return (
            bb_w - 2 * x,
            bb_h - 2 * y
        )


    def crop_around_center(self, image, width, height):
        """
        Given a NumPy / OpenCV 2 image, crops it to the given width and height,
        around it's centre point
        """

        image_size = (image.shape[1], image.shape[0])
        image_center = (int(image_size[0] * 0.5), int(image_size[1] * 0.5))

        if(width > image_size[0]):
            width = image_size[0]

        if(height > image_size[1]):
            height = image_size[1]

        x1 = int(image_center[0] - width * 0.5)
        x2 = int(image_center[0] + width * 0.5)
        y1 = int(image_center[1] - height * 0.5)
        y2 = int(image_center[1] + height * 0.5)

        return image[y1:y2, x1:x2]

    def __call__(self, image):
        rand = random.uniform(0,1)
        if rand < self.probability:
            img_file = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            image_height, image_width = img_file.shape[0:2]
            rotate = random.randint(0, 360)
            rotate_rad = rotate*0.0174532925
            image_rotated = self.rotate_image(img_file, rotate)
            image_rotated_cropped = self.crop_around_center(
                        image_rotated,
                        *self.largest_rotated_rect(
                        image_width,
                        image_height,
                        math.radians(rotate)
                        )
                    )
            img_convert = cv2.cvtColor(image_rotated_cropped, cv2.COLOR_BGR2RGB)
            img_pil_transformed = Image.fromarray(img_convert)
            return img_pil_transformed
        return image

class GaussianNoise():
    """ Add gaussian noise to a image """
    def __init__(self, sigma):
        self.sigma = sigma
    def __call__(self, image):
        image_array = np.asarray(image)
        noise_img = random_noise(image_array, var=0.05**2)
        noise_img = (255*noise_img).astype(np.uint8)
        return Image.fromarray(noise_img)

class GaussianNoiseTensor():
    """ Add gaussian noise to a tensor """
    def __init__(self, variance=0.1**2, mean=0):
        self.mean = mean
        self.variance = variance
    def __call__(self, images):
        #Images is a tensor that requires_grad
        image_clone = images.cpu()
        image_array = image_clone.numpy()
        noise_img = random_noise(image_array, var=self.variance)
        noise_img = torch.from_numpy(noise_img).float()
        noise_img = torch.from_numpy(image_array)
        return noise_img


def add_gaussian_noise_to_tensor(img, variance = 0.05**2, mean=0):
    noise = img.data.new(img.size()).normal_(mean, variance)
    return img + noise
