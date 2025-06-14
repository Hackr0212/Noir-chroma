import math
import os
import time

import pygame
from pygame.locals import *

try:
    import live2d.v3 as live2d
    from live2d.v3 import StandardParams
    from live2d.utils import log
    from live2d.utils.lipsync import WavHandler
except ImportError:
    raise ImportError("live2d-py is not installed. Please run 'pip install live2d-py'.")

# Set the path to your Live2D model directory (update this if you add your own model)
MODEL_PATH = os.environ.get("LIVE2D_MODEL_PATH", "live2d_model")
MODEL_JSON = None

# Try to find a .model3.json file in the model directory
for root, dirs, files in os.walk(MODEL_PATH):
    for file in files:
        if file.endswith(".model3.json"):
            MODEL_JSON = os.path.join(root, file)
            break
    if MODEL_JSON:
        break

if not MODEL_JSON:
    raise FileNotFoundError(f"No .model3.json file found in {MODEL_PATH}. Please add a Live2D Cubism 3+ model.")

def main():
    pygame.init()
    pygame.mixer.init()
    live2d.init()

    display = (500, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Live2D PyGame Demo")

    if live2d.LIVE2D_VERSION == 3:
        live2d.glewInit()

    model = live2d.LAppModel()
    model.LoadModelJson(MODEL_JSON)
    model.Resize(*display)

    running = True
    dx = 0.0
    dy = 0.0
    scale = 1.0

    # Disable auto blink and breath for demo
    model.SetAutoBlinkEnable(False)
    model.SetAutoBreathEnable(False)

    wavHandler = WavHandler()
    lipSyncN = 3
    audioPlayed = False
    currentTopClickedPartId = None
    partIds = model.GetPartIds()

    def getHitFeedback(x, y):
        hitPartIds = model.HitPart(x, y, False)
        if currentTopClickedPartId is not None:
            pidx = partIds.index(currentTopClickedPartId)
            model.SetPartOpacity(pidx, 1)
            model.SetPartMultiplyColor(pidx, 1.0, 1.0, 1.0, 1)
        if len(hitPartIds) > 0:
            return hitPartIds[0]
        return None

    radius_per_frame = math.pi * 10 / 1000 * 0.5
    deg_max = 5
    progress = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                currentTopClickedPartId = getHitFeedback(x, y)
                model.SetRandomExpression()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    dx -= 0.1
                elif event.key == pygame.K_RIGHT:
                    dx += 0.1
                elif event.key == pygame.K_UP:
                    dy += 0.1
                elif event.key == pygame.K_DOWN:
                    dy -= 0.1
                elif event.key == pygame.K_i:
                    scale += 0.1
                elif event.key == pygame.K_u:
                    scale -= 0.1
                elif event.key == pygame.K_r:
                    model.StopAllMotions()
                    model.ResetPose()
                elif event.key == pygame.K_e:
                    model.ResetExpression()
            if event.type == pygame.MOUSEMOTION:
                model.Drag(*pygame.mouse.get_pos())
                currentTopClickedPartId = getHitFeedback(*pygame.mouse.get_pos())
        if not running:
            break
        progress += radius_per_frame
        deg = math.sin(progress) * deg_max
        model.Rotate(deg)
        model.Update()
        if currentTopClickedPartId is not None:
            pidx = partIds.index(currentTopClickedPartId)
            model.SetPartOpacity(pidx, 0.5)
            model.SetPartMultiplyColor(pidx, .0, .0, 1., .9)
        if wavHandler.Update():
            model.SetParameterValue(StandardParams.ParamMouthOpenY, wavHandler.GetRms() * lipSyncN)
        model.SetOffset(dx, dy)
        model.SetScale(scale)
        live2d.clearBuffer(1.0, 0.0, 0.0, 0.0)
        model.Draw()
        pygame.display.flip()
        pygame.time.wait(10)
    live2d.dispose()
    pygame.quit()
    quit()

if __name__ == "__main__":
    main()
