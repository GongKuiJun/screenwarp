#!/usr/bin/python

import cv2
import numpy
import wand.image
import wand.color
import wand.drawing
import sys
import logging
import argparse
import operator
import os.path

logger = logging.getLogger(__name__)

def parse_cmdline():
    parser = argparse.ArgumentParser(description='''
        TODO: insert description.'''
    )
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose output")
    parser.add_argument('-q', '--quiet', action='store_true', help="Output errors only")
    parser.add_argument('-W', '--width', type=int, help="Target screen width. This will be the width of the output images.", default=1920)
    parser.add_argument('-H', '--height', type=int, help="Target screen height. This will be the height of the output images.", default=1080)
    parser.add_argument('-r', '--rows', type=int, help="Number of squares per row", default=16)
    parser.add_argument('-c', '--cols', type=int, help="Number of inner corners per column", default=9)
    parser.add_argument('-a', '--align', action='store_true', help="Consider the bottom row of points as a reference line")
    parser.add_argument('infile', help="Image file")
    parser.add_argument('outfile', help="Image file")
    args = parser.parse_args()

    if args.verbose: loglevel = logging.DEBUG
    elif args.quiet: loglevel = logging.ERROR
    else:            loglevel = logging.INFO

    logging.basicConfig(level=loglevel, format='%(asctime)s %(levelname)s %(message)s')

    return args


def main():
    args = parse_cmdline()

    screen_width = args.width
    screen_height = args.height

    square_width = screen_width / args.cols
    square_height = screen_height / args.rows
    cols = args.cols + 1
    rows = args.rows + 1

    captured_grid = {}
    for i in range(rows): captured_grid[i] = {}

    corrected_grid = {}
    for i in range(rows): corrected_grid[i] = {}

    inverse_grid = {}
    for i in range(rows): inverse_grid[i] = {}


    base_grid = get_base_grid(rows, cols, square_width, square_height)

    draw_grid("out0.png", base_grid, 1280+20, 720+20, 10, 10)

    img = cv2.imread(args.infile, 0)
    if img is None:
        logger.error("File '%s' could not be read", args.infile)
        exit(1)

    status, data = cv2.findChessboardCorners(img, (rows-2, cols-2), flags=cv2.cv.CV_CALIB_CB_ADAPTIVE_THRESH)
    if status == False:
        logger.error("Failed to parse checkerboard pattern in image")
        exit(2)

    r = 1
    c = 1

    for row in data:
        captured_grid[r][cols-c-1] = [ row[0][0], row[0][1] ]
        if r == (rows-2):
            r = 1
            c += 1
        else:
            r += 1

    for i in range(1, cols-1):
        captured_grid[0][i] = predict(captured_grid[1][i], captured_grid[2][i])
        captured_grid[rows-1][i] = predict(captured_grid[rows-2][i], captured_grid[rows-3][i])

    for i in range(1, rows-1):
        captured_grid[i][0] = predict(captured_grid[i][1], captured_grid[i][2])
        captured_grid[i][cols-1] = predict(captured_grid[i][cols-2], captured_grid[i][cols-3])

    captured_grid[0][0] = predict(captured_grid[1][1], captured_grid[2][2])
    captured_grid[rows-1][0] = predict(captured_grid[rows-2][1], captured_grid[rows-3][2])
    captured_grid[0][cols-1] = predict(captured_grid[1][cols-2], captured_grid[2][cols-3])
    captured_grid[rows-1][cols-1] = predict(captured_grid[rows-2][cols-2], captured_grid[rows-3][cols-3])


    draw_grid("out1.png", captured_grid, 1280+20, 768+20, 10, 10)

    if args.align:
        # The bottom edge is the line we consider "straight". Straighten image using bottom edge as ref and align to bottom of pic
        for c in range(cols):
            offset = captured_grid[rows-1][c]
            for r in range(rows):
                corrected_grid[r][c] = [ captured_grid[r][c][0], captured_grid[r][c][1] - offset[1] + screen_height ]
    else:
        for c in range(cols):
            for r in range(rows):
                corrected_grid[r][c] = [ captured_grid[r][c][0], captured_grid[r][c][1] ]

    draw_grid("out2.png", corrected_grid, 1280+20, 768+20, 10, 10)

    mins, maxes = get_bounding_box(corrected_grid)
    logger.info("Edges: %s %s - %s %s", mins[0], mins[1], maxes[0], maxes[1])
    mins, maxes = get_contained_box(corrected_grid)
    logger.info("Edges: %s %s - %s %s", mins[0], mins[1], maxes[0], maxes[1])
    edgex = mins[0] + (1280 -  maxes[0])
    edgey = mins[1] + (720 -  maxes[1])
    mulx = 1280 / (1280 - edgex)
    muly = 720 / (720 - edgey)

    logger.info("mulx: %s, muly = %s", mulx, muly)

    # Scale to screen size
    for r in range(rows):
        for c in range(cols):
            corrected_grid[r][c][0] = (corrected_grid[r][c][0] - mins[0]) * mulx
            corrected_grid[r][c][1] = (corrected_grid[r][c][1] - mins[1]) * muly

    draw_grid("out3.png", corrected_grid, 1280+20, 768+20, 10, 10)
    for r in range(rows-1, -1, -1):
        for c in range(cols):

            logger.info(corrected_grid[r][c])
            inverse_grid[r][c] = predict(base_grid[r][c], corrected_grid[r][c])
            logger.info("[%s][%s] %s -> %s -> %s", r, c, corrected_grid[r][c][0], base_grid[r][c][0], inverse_grid[r][c][0])
            logger.info("[%s][%s] %s -> %s -> %s", r, c, corrected_grid[r][c][1], base_grid[r][c][1], inverse_grid[r][c][1])

    draw_grid("out4.png", inverse_grid, 1280+20, 768+20, 10, 10)


    with open(args.outfile, 'w+') as f:
        f.write("{0} {1}\n".format(rows, cols))
        for r in range(rows-1, -1, -1):
            for c in range(cols):
                if c == 0 or c == cols-1: intensity = 0.2
                else: intensity = 1
                f.write("{0} {1} {2} {3} {4}\n".format(c / float(cols), r / float(rows),
                    inverse_grid[r][c][0]/screen_width, inverse_grid[r][c][1]/screen_height, intensity))

    exit(0)

def predict(curr, prev):
    delta = map(operator.sub, curr, prev)
    logger.info(delta)
    return map(operator.add, curr, delta)


def draw_grid(filename, grid, width, height, xoff, yoff):
    image = wand.image.Image(width=width, height=height, background=wand.color.Color('#fff'))

    with wand.drawing.Drawing() as draw:
        draw.fill_color = wand.color.Color('#f00')
        for r in range(len(grid)):
            # draw.fill_color = wand.color.Color('#{0:x}{0:x}{0:x}'.format(r*2))
            for c in range(len(grid[r])):
                #logger.info("r: %s, c: %s", r, c)
                x = grid[r][c][0] + xoff
                y = grid[r][c][1] + yoff
                draw_point(draw, x, y)

        draw.draw(image)
    image.save(filename=filename)


def draw_point(draw, x, y):
    draw.point(x, y)
    draw.point(x+1, y)
    draw.point(x-1, y)
    draw.point(x, y+1)
    draw.point(x, y-1)


def get_base_grid(rows, cols, square_width, square_height):
    base_grid = {}
    for r in range(rows):
        for c in range(cols):
            #ci = cols - c -1
            if not r in base_grid:
                base_grid[r] = {}
            base_grid[r][c] = [ c * square_width, r * square_height ]
            # logger.debug("ref[%s][%s] = [ %s %s ]", r, ci, (r)*square_width, (c)*square_height)

    return base_grid


def get_contained_box(grid):
    mins = [None, None]
    maxes = [None, None]

    rows = len(grid)
    cols = len(grid[0])
    for r in range(rows):
        for c in range(cols):
            curr = grid[r][c]
            if r == 0:
                if mins[1] == None or mins[1] < curr[1]:
                    mins[1] = curr[1]
            elif r == (rows-1):
                if maxes[1] == None or maxes[1] > curr[1]:
                    maxes[1] = curr[1]

            if c == 0:
                if mins[0] == None or mins[0] < curr[0]:
                    mins[0] = curr[0]
            elif c == (cols-1):
                if maxes[0] == None or maxes[0] > curr[0]:
                    maxes[0] = curr[0]

    return (mins, maxes)


def get_bounding_box(grid):
    mins = [None, None]
    maxes = [None, None]

    for r in range(len(grid)):
        for c in range(len(grid[r])):
            curr = grid[r][c]
            if mins[0] == None or mins[0] > curr[0]:
                mins[0] = curr[0]
            if mins[1] == None or mins[1] > curr[1]:
                mins[1] = curr[1]
            if maxes[0] == None or maxes[0] < curr[0]:
                maxes[0] = curr[0]
            if maxes[1] == None or maxes[1] < curr[1]:
                maxes[1] = curr[1]

    return(mins, maxes)


# call main()
if __name__ == '__main__':
    main()