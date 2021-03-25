from PIL import Image
import numpy as np
import time
from .utils import colour_functions as cf
from .camera import Camera
from .utils.constants import *
from .utils.vector3 import vec3, rgb
from .ray import Ray, get_raycolor, get_distances
from . import lights
from .backgrounds.skybox import SkyBox
from .backgrounds.panorama import Panorama

from threading import Thread

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QObject, QThread, pyqtSignal

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):
        #print(type(self._target))
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return


class Scene():
    def __init__(self, ambient_color = rgb(0.01, 0.01, 0.01), n = vec3(1.0,1.0,1.0)) :
        # n = index of refraction (by default index of refraction of air n = 1.)
        
        self.scene_primitives = []
        self.collider_list = []
        self.shadowed_collider_list = []
        self.Light_list = []
        self.importance_sampled_list = []
        self.ambient_color = ambient_color
        self.n = n
        self.importance_sampled_list = []
    def add_Camera(self, look_from, look_at, **kwargs):
        self.camera = Camera(look_from, look_at, **kwargs)


    def add_PointLight(self, pos, color):
        self.Light_list += [lights.PointLight(pos, color)]
        
    def add_DirectionalLight(self, Ldir, color):
        self.Light_list += [lights.DirectionalLight(Ldir.normalize() , color)]  

    def add(self,primitive, importance_sampled = False):
        self.scene_primitives += [primitive]
        self.collider_list += primitive.collider_list

        if importance_sampled == True:
            self.importance_sampled_list += [primitive]

        if primitive.shadow == True:
            self.shadowed_collider_list += primitive.collider_list
            
        
    def add_Background(self, img, light_intensity = 0.0, blur =0.0 , spherical = False):

        primitive = None
        if spherical == False:
            primitive = SkyBox(img, light_intensity = light_intensity, blur = blur)
        else:
            primitive = Panorama(img, light_intensity = light_intensity, blur = blur)

        self.scene_primitives += [primitive]        
        self.collider_list += primitive.collider_list

        
    def render(self, progResStep, worker, threads, samples_per_pixel, progress_bar = False):

        print ("Rendering...")

        t0 = time.time()
        calc_rays = []
        calc_rays_t = []
        color_RGBlinearQuarter = rgb(0., 0., 0.)
        color_RGBlinearHalf = rgb(0., 0., 0.)

        if progress_bar == True:


            try:
                import progressbar

            except ModuleNotFoundError:
                 print("progressbar module is required. \nRun: pip install progressbar")
            
            bar = progressbar.ProgressBar()
            for i in bar(range(samples_per_pixel)):
                color_RGBlinear += get_raycolor(self.camera.get_ray(self.n), scene = self)
                bar.update(i)
        else:


            for i in range(samples_per_pixel):

                if i == 0 and progResStep == 0:

                    tempQuarterCam = Camera(self.camera.look_from, self.camera.look_at,
                                            screen_width = int(self.camera.screen_width / 4),
                                            screen_height = int(self.camera.screen_height / 4),
                                            focal_distance = self.camera.focal_distance,
                                            field_of_view = self.camera.field_of_view)

                    color_RGBlinearQuarter += get_raycolor(tempQuarterCam.get_ray(self.n)[0], scene=self)

                    q_color = cf.sRGB_linear_to_sRGB(color_RGBlinearQuarter.to_array())

                    q_img_RGB = []
                    for c in q_color:
                        # average ray colors that fall in the same pixel. (antialiasing)
                        q_img_RGB += [Image.fromarray((255 * np.clip(c, 0, 1).reshape((tempQuarterCam.screen_height, tempQuarterCam.screen_width))).astype(np.uint8), "L")]

                    q_img = Image.merge("RGB", q_img_RGB)
                    q_img.save(f"images/progThread{i + 1}.png")

                    worker.samplePass.emit(i)

                    print ("Render Took", time.time() - t0)

                elif i == 1 and progResStep == 1:

                    tempHalfCam = Camera(self.camera.look_from, self.camera.look_at,
                                            screen_width=int(self.camera.screen_width / 2),
                                            screen_height=int(self.camera.screen_height / 2),
                                            focal_distance = self.camera.focal_distance,
                                            field_of_view = self.camera.field_of_view)

                    color_RGBlinearHalf += get_raycolor(tempHalfCam.get_ray(self.n)[0], scene=self)

                    h_color = cf.sRGB_linear_to_sRGB(color_RGBlinearHalf.to_array())

                    h_img_RGB = []
                    for c in h_color:
                        # average ray colors that fall in the same pixel. (antialiasing)
                        h_img_RGB += [Image.fromarray((255 * np.clip(c, 0, 1).reshape((tempHalfCam.screen_height, tempHalfCam.screen_width))).astype(np.uint8), "L")]

                    h_img = Image.merge("RGB", h_img_RGB)
                    h_img.save(f"images/progThread{i + 1}.png")

                    worker.samplePass.emit(i)

                    print ("Render Took", time.time() - t0)

                elif progResStep == 2:

                    separated_rays = self.camera.get_ray(self.n, threads=threads)

                    if i == 0:
                        for r in range(len(separated_rays)):
                            calc_rays.append(rgb(0., 0., 0.))
                            calc_rays_t.append([None])

                    for r in range(len(separated_rays)):
                        calc_rays_t[r] = ThreadWithReturnValue(target=get_raycolor, args=(separated_rays[r], self))
                        calc_rays_t[r].start()

                    for r in range(len(separated_rays)):
                        calc_rays[r] += calc_rays_t[r].join()

                    if threads == 1:
                        p_color_RGBlinear = calc_rays[0] / (i + 1)

                    else:
                        for cr in range(len(calc_rays) - 1):
                            if cr == 0:
                                modded_color_x = np.concatenate((calc_rays[cr].x, calc_rays[cr + 1].x))
                                modded_color_y = np.concatenate((calc_rays[cr].y, calc_rays[cr + 1].y))
                                modded_color_z = np.concatenate((calc_rays[cr].z, calc_rays[cr + 1].z))
                            else:
                                modded_color_x = np.concatenate((modded_color_x, calc_rays[cr + 1].x))
                                modded_color_y = np.concatenate((modded_color_y, calc_rays[cr + 1].y))
                                modded_color_z = np.concatenate((modded_color_z, calc_rays[cr + 1].z))

                        modded_color = vec3(modded_color_x, modded_color_y, modded_color_z)

                        p_color_RGBlinear = modded_color / (i + 1)


                    p_color = cf.sRGB_linear_to_sRGB(p_color_RGBlinear.to_array())

                    p_img_RGB = []
                    for c in p_color:
                        # average ray colors that fall in the same pixel. (antialiasing)
                        p_img_RGB += [Image.fromarray((255 * np.clip(c, 0, 1).reshape((self.camera.screen_height, self.camera.screen_width))).astype(np.uint8), "L")]

                    p_img = Image.merge("RGB", p_img_RGB)
                    p_img.save(f"images/progThread{i + 3}.png")
                    worker.samplePass.emit(i + 2)
                    #p_img.show()
                    print("Render Took", time.time() - t0)


        #Original block that ran for every sample

        #average samples per pixel (antialiasing)
        #color_RGBlinear = color_RGBlinear/samples_per_pixel
        #gamma correction
        #color = cf.sRGB_linear_to_sRGB(color_RGBlinear.to_array())

        #img_RGB = []
        #for c in color:
            # average ray colors that fall in the same pixel. (antialiasing) 
            #img_RGB += [Image.fromarray((255 * np.clip(c, 0, 1).reshape((self.camera.screen_height, self.camera.screen_width))).astype(np.uint8), "L") ]

        #return Image.merge("RGB", img_RGB)


    def get_distances(self): #Used for debugging ray-primitive collisions. Return a grey map of objects distances.

        print ("Rendering...")
        t0 = time.time()
        color_RGBlinear = get_distances( self.camera.get_ray(self.n), scene = self)
        #gamma correction
        color = color_RGBlinear.to_array()
        
        print ("Render Took", time.time() - t0)

        img_RGB = [Image.fromarray((255 * np.clip(c, 0, 1).reshape((self.camera.screen_height, self.camera.screen_width))).astype(np.uint8), "L") for c in color]
        return Image.merge("RGB", img_RGB)