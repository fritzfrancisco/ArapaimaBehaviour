#!/usr/bin/env python3

import cv2
import os
import numpy as np
import argparse
from datetime import datetime, time
from pypylon import pylon

ap = argparse.ArgumentParser(
    description='Input specific output pathway and framerate')
ap.add_argument("-o", "--output_directory", required=False,
                default=None, help="path to output directory")
ap.add_argument("-wo", "--width", required=False,
                default=2048, type=int, help="output width")
ap.add_argument("-ho", "--height", required=False,
                default=2048, type=int, help="output height")
ap.add_argument("-r", "--framerate", type=int, default=30,
                required=False, help="acquisition frame rate")
ap.add_argument("-c", "--chunk_size", required=False,
                default=50000, type=int, help="output chunk size in frames")
ap.add_argument("-sc", "--scaling", required=False, default=1,
                type=float, help="scaling factor for output e.g 1, 0.5, 0.25")
ap.add_argument("-cc", "--codec", required=False, default='mp4v',
                type=str, help="video codec [FOURCC]")
ap.add_argument("-exp", "--exposure", required=False,
                default=50000, type=int, help="exposure time")
ap.add_argument("-gs", "--gain_setting", required=False,
                default='Continuous', type=str, help="gain settings ['Once', 'Continuous', 'Off']")
ap.add_argument("-s", "--show", default=True, help="show live video")
ap.add_argument("-t", "--duration", default=-1, type=int,
                help="video duration (seconds)")
ap.add_argument("-f", "--filetype", default='.mp4', type=str,
                help="video filetype extension")
args = vars(ap.parse_args())
print(args)


def change_chunk():
    '''function that changes chunk number and output file accordingly.
    It accesses the global input arguments as well as chunk_idx to do so.'''
    global camera, args, chunk_idx
    dateTimeObj = datetime.now()
    timestamp = dateTimeObj.strftime("%Y%m%d_%H%M%S")
    fourcc = cv2.VideoWriter_fourcc(*args['codec'])
    fname = str(str(args['output_directory']) + str(chunk_idx).zfill(6) + '_' + str(camera.GetDeviceInfo().GetModelName()).replace('-', '_') + '_' + str(camera.GetDeviceInfo().GetSerialNumber()) + '_exp' + str(args['exposure']) +
                '_r' + str(args["framerate"]) + '_res' + str(args['scaling']) + '_' + str(timestamp) + str(args['filetype']))
    out = cv2.VideoWriter(filename=fname, fourcc=fourcc,
                          fps=25, frameSize=(int(args['width']*args['scaling']),int(args['height']*args['scaling'])),isColor=1)
    ret = False
    print('Output file: ', fname)
    return ret, out


# Create timestamp
dateTimeObj = datetime.now()
timestamp = dateTimeObj.strftime("%Y%m%d_%H%M%S")

# Conecting to the first available camera
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
print('Camera: ', camera)

# Open camera instance
camera.Open()

# Set exposure time
camera.ExposureTime.SetValue(args['exposure'])

# Set gain
camera.GainAuto.SetValue(args['gain_setting'])

# Set acquisition frame rate
camera.AcquisitionFrameRateEnable.SetValue(True)
camera.AcquisitionFrameRate.SetValue(float(args['framerate']))
print('Image Aquisition Rate :', camera.AcquisitionFrameRate.GetValue())

# Set image dimensions
camera.Width.SetValue(args['width'])
camera.Height.SetValue(args['height'])

# Grabing Continusely (video) with minimal delay
# camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
# camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
images_to_grab = args['framerate'] * args['duration']
camera.StartGrabbingMax(images_to_grab, pylon.GrabStrategy_OneByOne)


# Set up video window
if args['show'] == True:
    cv2.namedWindow(str('Basler Capture ' +
                    str(camera.GetDeviceInfo().GetSerialNumber())), cv2.WINDOW_NORMAL)

# converting to opencv bgr format
converter = pylon.ImageFormatConverter()
converter.OutputPixelFormat = pylon.PixelType_BGR8packed
converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

# frame counter
frame_idx = 0

# chunk counter
chunk_idx = 0

# initate with first chunk
change, out = change_chunk()

while camera.IsGrabbing():
    grabResult = camera.RetrieveResult(
        5000, pylon.TimeoutHandling_ThrowException)

    if grabResult.GrabSucceeded():

        # Change chunk
        if change == True:
            change, out = change_chunk()

        # Access the image data
        image = converter.Convert(grabResult)
        img = image.GetArray()

        if args['scaling'] != 1:
            # Resize output image based on scaling
            img = cv2.resize(img, None, fy=args['scaling'], fx=args['scaling'])

        # add timestamp in output image
        img = cv2.putText(img, datetime.now().strftime("%Y%m%d %H:%M:%S"), (
            15, img.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, lineType=cv2.LINE_AA)

        if args['output_directory'] != None:
            
            # Convert image to gray scale
            # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Save to video container
            out.write(img)

        if args['show'] == True:
            cv2.imshow(str('Basler Capture ' +
                       str(camera.GetDeviceInfo().GetSerialNumber())), img)
            k = cv2.waitKey(1)
            if k == 27:
                camera.StopGrabbing()
                camera.Close()
                if args['output_directory'] != None:
                    out.release()
                if args['show'] == True:
                    cv2.destroyAllWindows()
                break
        
        # End recording if duration is exceeded
        if (args['duration'] > 0) and (frame_idx >= int(args['duration']*args['framerate'])):
            camera.StopGrabbing()
            camera.Close()
            if args['output_directory'] != None:
                out.release()
            if args['show'] == True:
                cv2.destroyAllWindows()
            break

        print(img.shape)

    else:
        if args['output_directory'] != None:
            
            # Create black image
            blank = np.ones((img.shape[0],img.shape[1],3),np.uint8) * 255

            # Save to video container
            out.write(blank)

        # End recording if duration is exceeded
        if (args['duration'] > 0) and (frame_idx >= int(args['duration']*args['framerate'])):
            camera.StopGrabbing()
            camera.Close()
            if args['output_directory'] != None:
                out.release()
            if args['show'] == True:
                cv2.destroyAllWindows()
            break
        print('Grab result unsuccessful!')
        # break

    grabResult.Release()
    frame_idx += 1

    # Change to next chunk
    if frame_idx % args['chunk_size'] == 0:
        change = True
        chunk_idx += 1

    print(frame_idx)

# Releasing the resource
print('Finished recording! ',str(camera.GetDeviceInfo().GetSerialNumber()))
camera.StopGrabbing()
camera.Close()

if args['output_directory'] != None:
    out.release()
if args['show'] == True:
    cv2.destroyAllWindows()
