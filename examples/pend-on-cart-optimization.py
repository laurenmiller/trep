import numpy as np

from itertools import product
import sys
import trep
from trep import tx, ty, tz, rx, ry, rz
import trep.discopt as discopt

import math
from math import sin, cos
from math import pi as mpi
import pygame


class Viewer(object):
    def __init__(self, system, t, q, qd):
        self.system = system
        self.t = t
        self.q = q
        self.qd = qd

        self.window_width = 800
        self.window_height = 600
        self.scale = 200
        self.camera_x = 0

        pygame.init()

        self.frame_index = 0
        self.paused = True
        self.clock = pygame.time.Clock()
        self.clock.tick(0)

        self.cart_color = [
            pygame.Color(200, 200, 200),
            pygame.Color(230, 230, 230)
            ]
        self.cart_height = 20
        self.cart_width = 80
        self.link_color = [
            pygame.Color(0, 0, 0),
            pygame.Color(200, 200, 200)
            ]
        self.link_width = 5
        self.weight_color = [
            pygame.Color(0, 66, 66),
            pygame.Color(0, 200, 200)
            ]
            
        self.weight_radius = 20

    def transform(self, point):
        x = point[0] 
        y = point[1]

        x = int(self.window_width/2 + self.scale*(x - self.camera_x))
        y = int(self.window_height/2 - self.scale*y)
        return (x,y)

    def draw_cart(self, q, colors=0):
        self.system.q = q

        cart_pos = self.transform(self.system.get_frame('Cart').p())
        pygame.draw.rect(self.screen, self.cart_color[colors],
                         pygame.Rect(cart_pos[0] - self.cart_width/2,
                                     cart_pos[1] - self.cart_height/2,
                                     self.cart_width, self.cart_height))
        pygame.draw.line(self.screen, self.link_color[colors],
                         self.transform(self.system.get_frame('Cart').p()),
                         self.transform(self.system.get_frame('Pendulum').p()),
                         self.link_width)
        pygame.draw.circle(self.screen, self.link_color[colors],
                           self.transform(self.system.get_frame('Cart').p()),
                           self.link_width/2)
        pygame.draw.circle(self.screen, self.weight_color[colors],
                           self.transform(self.system.get_frame('Pendulum').p()),
                           self.weight_radius)

    def draw_ground(self):
        color1 = pygame.Color(100, 100, 100)
        period = 50.0 # pixels
        color2 = pygame.Color(150, 150, 150)
        duty = 25.0 # pixels
        slant = 5.0 # pixels
        thickness = 10
        top = self.window_height/2 - thickness/2

        pygame.draw.rect(self.screen, color1,
                         pygame.Rect(0, top, self.window_width, thickness))

        # Draw alternating rectangles to give the appearance of movement.
        left_edge = -self.scale*self.camera_x
        i0 = int(math.floor(left_edge/period))
        i1 = int(math.ceil(i0 + self.window_width/period))

        for i in range(i0-1, i1+1):
            #pygame.draw.rect(screen, color2, pygame.Rect(i*period - left_edge, top,
            #                                             duty, thickness))
            x = i*period - left_edge
            pygame.draw.polygon(self.screen, color2, (
                (x, top), (x+duty, top),
                (x+duty+slant, top+thickness-1), (x+slant, top+thickness-1)))

    def draw_time(self):
        # Create a font
        font = pygame.font.Font(None, 17)
        
        # Render the text
        txt = 't = %4.2f' % self.t[self.frame_index]
        text = font.render(txt , True, (0, 0, 0))

        # Create a rectangle
        textRect = text.get_rect()
        
        # Center the rectangle
        textRect.right = self.window_width - 10
        textRect.top = 10
        #textRect.centerx = screen.get_rect().centerx
        #textRect.centery = screen.get_rect().centery
        # Blit the text
        self.screen.blit(text, textRect)
        
    def togglepause(self):        
        if self.paused:
            self.paused = False
            self.clock.tick(0) # Reset the clock start time
        elif self.paused == False and self.frame_index == len(self.t)-1:
            self.frame_index = 0
        else:
            self.paused = True
        
    def main(self):
        self.window = pygame.display.set_mode((self.window_width, self.window_height))
        pygame.display.set_caption('trajectory optimization')
        self.screen = pygame.display.get_surface()
        self.run_viewer = True        
        
        while self.run_viewer:
            for event in pygame.event.get(): 
                if event.type == pygame.QUIT or \
                   (event.type == pygame.KEYDOWN and event.key == pygame.K_q) or \
                   (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    self.run_viewer = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    self.togglepause()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    self.frame_index = 0
                    
            self.screen.fill(pygame.Color('white'))
            self.draw_ground()
            self.draw_cart(self.qd[self.frame_index], 1)
            self.draw_cart(self.q[self.frame_index], 0)
            self.draw_time()
            pygame.display.flip()

            if not self.paused:
                if self.frame_index < len(self.t)-1:
                    self.frame_index += 1
                    if self.frame_index < len(self.t):
                        delay = (self.t[self.frame_index]-self.t[self.frame_index-1])
                    else:
                        delay = 1.0/60.0
            else:
                delay = 1/60.0
            self.clock.tick(1.0/delay)



def build_system(torque_force=False):
    cart_mass = 10.0
    pendulum_length = 1.0
    pendulum_mass = 1.0

    system = trep.System()
    frames = [
        tx('x', name='Cart', mass=cart_mass), [
            rz('theta'), [
                ty(-pendulum_length, name="Pendulum", mass=pendulum_mass)]]]
    system.import_frames(frames)
    trep.potentials.Gravity(system, (0, -9.8, 0))
    trep.forces.Damping(system, 0.01)
    trep.forces.JointForce(system, 'x', 'x-force')
    if torque_force:
        trep.forces.JointForce(system, 'theta', 'theta-force')
    return system

def generate_desired_trajectory(system, t, amp=130*mpi/180):
    qd = np.zeros((len(t), system.nQ))
    theta_index = system.get_config('theta').index
    for i,t in enumerate(t):
        if t >= 3.0 and t <= 7.0:
            qd[i, theta_index] = (1 - cos(2*mpi/4*(t-3.0)))*amp/2
    return qd

def make_state_cost(dsys, base, x, theta):
    weight = base*np.ones((dsys.nX,))
    weight[system.get_config('x').index] = x
    weight[system.get_config('theta').index] = theta
    return np.diag(weight)

def make_input_cost(dsys, base, x, theta=None):
    weight = base*np.ones((dsys.nU,))
    if theta is not None:
        weight[system.get_input('theta-force').index] = theta
    weight[system.get_input('x-force').index] = x
    return np.diag(weight)                    



# Build cart system with torque input on pendulum.
system = build_system(True)
mvi = trep.MidpointVI(system)
t = np.arange(0.0, 10.0, 0.01)
dsys_a = discopt.DSystem(mvi, t)


# Generate an initial trajectory
(X,U) = dsys_a.build_trajectory()
for k in range(dsys_a.kf()):
    if k == 0:
        dsys_a.set(X[k], U[k], 0)
    else:
        dsys_a.step(U[k])
    X[k+1] = dsys_a.f()


# Generate cost function
qd = generate_desired_trajectory(system, t, 130*mpi/180)
(Xd, Ud) = dsys_a.build_trajectory(qd)
Qcost = make_state_cost(dsys_a, 0.01, 0.01, 100.0)
Rcost = make_input_cost(dsys_a, 0.01, 0.01, 0.01)
cost = discopt.DCost(Xd, Ud, Qcost, Rcost)

optimizer = discopt.DOptimizer(dsys_a, cost)

# Perform the first optimization
optimizer.first_order_iterations = 4
finished, X, U = optimizer.optimize(X, U, max_steps=40)

# Increase the cost of the torque input
cost.R = make_input_cost(dsys_a, 0.01, 0.01, 100.0)
optimizer.first_order_iterations = 4
finished, X, U = optimizer.optimize(X, U, max_steps=40)

# Increase the cost of the torque input
cost.R = make_input_cost(dsys_a, 0.01, 0.01, 1000000.0)
optimizer.first_order_iterations = 4
finished, X, U = optimizer.optimize(X, U, max_steps=40)


# The torque should be really tiny now, so we can hopefully use this
# trajectory as the initial trajectory of the real system.  

# Build a new system without the extra input
system = build_system(False)
mvi = trep.MidpointVI(system)
dsys_b = discopt.DSystem(mvi, t)

# Map the optimized trajectory for dsys_a to dsys_b
(X, U) = dsys_b.import_trajectory(dsys_a, X, U)

# Simulate the new system starting from the initial condition of our
# last optimization and using the x-force input.
for k in range(dsys_b.kf()):
    if k == 0:
        dsys_b.set(X[k], U[k], 0)
    else:
        dsys_b.step(U[k])
    X[k+1] = dsys_b.f()

# Generate a new cost function for the current system.
qd = generate_desired_trajectory(system, t, 130*mpi/180)
(Xd, Ud) = dsys_b.build_trajectory(qd)
Qcost = make_state_cost(dsys_b, 0.01, 0.01, 100.0)
Rcost = make_input_cost(dsys_b, 0.01, 0.01)
cost = discopt.DCost(Xd, Ud, Qcost, Rcost)

optimizer = discopt.DOptimizer(dsys_b, cost)

# Perform the optimization on the real system
optimizer.first_order_iterations = 4
finished, X, U = optimizer.optimize(X, U, max_steps=40)

if '--novisual' not in sys.argv:
    q,p,v,u,rho = dsys_b.split_trajectory(X, U)
    view = Viewer(system, t, q, qd)
    view.main()


