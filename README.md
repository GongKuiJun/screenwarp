# screenwarp
Utility for calibrating displays in order to produce an image that looks right from a particular viewpoint. It is primarily aimed at projectors pointed at non-flat surfaces.

Note: the software is highly experimental. It was written over a weekend and has not been tested much. Questions, comments, suggestions for improvement and patches are most welcome.

## Usage

### Step 1: Generate Test Image

Use '''drawchessboard.py''' to output a chessboard image file of your choosing. Ideally you should choose the number of rows and columns based on your aspect ratio.
The default is 16 columns by 9 rows which will result in perfect squares on 16:9 aspect ratio screens.

    drawchessboard.py testpattern.png

### Step 2: Output Test Image on Screen

Use any graphics viewer capable of producing a full screen image to display the test pattern on your screen.

### Step 3: Take a Photo

Take a photo of the displayed result using any camera. Make sure you take the photo from the viewpoint you wish to calibrate the view for.
E.g. if you are calibrating a projector for viewing while sitting down, take the photo by sitting down rather than standing up.

### Step 4 (optional): Pre-process your Photo

Pre-process your photo for better reliability of detection. I have used the "Threshold" tool in Gimp to cleanly separate the black and white colours.
I've also found that the detection algorithm works better on small images (less than 1000px wide).

### Run '''screenwarp.py'''

Process your photo with '''screenwarp.py'''. Screenwarp will read your image and use OpenCV's findChessboardCorners method to locate the inner edges of the chessboard pattern.

    warpdetect.py DSCF1234.JPG calibration_points.warp

If Screenwarp fails to locate the pattern, try reducing the number of rows and columns by one or more. You could also try to resize your image to be smaller.

    warpdetect.py -r 8 -c 15 DSCF1234.png calibration_points.warp

If everything goes well, Screenwarp will do the following:

  - Create a grid with the locations of the "ideal" undistorted points. This grid should match the square corners in your original calibration image.
  - Since the checkboard detection algorithm does not detect the points around the edge, these will be made up based on the location of the inner set of points.
  - If the '''---align''' flag was used, the image is reshaped in such a way that the bottom set of rows are made into a straight line.
  This is useful for deliberately curved screens.
  - The points are then scaled to the size of the screen in such a way that the screen area fits entirely within the points.
  - Finally each point is moved to the the opposite side of its "ideal" location by taking the difference between the ideal and actual coordinates
  and adding the difference to the ideal coordinates.
  - The resulting points are then written to a the output file specified on the command line.

## Warp File Format

The output file format is quite simple:

    screenwarp VERSION ROWS COLS X_FLIP Y_FLIP U_FLIP V_FLIP
    X1 Y1 U1 V1 INTENSITY1
    X2 Y2 U2 V2 INTENSITY2
    .
    .
    Xn Yn Un Vn INTENSITYn

The first row is a header. It starts with an identifier that allows programs to check if they are reading a screenwarp file, then a version number which is an integer.
The current version is 1.
The following two fields specify the number of rows and columns. This determines the number of lines in the file which must match ROWS*COLS.
The `*_FLIP` fields are boolean values that instruct Flightgear to reverse the relevant column. This is mostly useful for debugging and may be removed in a future version.

The header is followed by a line for each point (ROWS*COLS points in total).
In each row, the first four values are X and Y coordinates as a percentage of the screen width or height respectively. These are values between 0 and 1.
Intensity is the brightness of the image at each point, also between 0 and 1. This is designed to be used for edge blending.
Currently the brightness is reduced at the left and right edges. This behaviour will be made configurable eventually.


### Examples

The images folder contains a bunch of images showing the calibration process, the images of the points generated by Screenwarp for visualisation purposes
and Flightgear using the corrected projection.

