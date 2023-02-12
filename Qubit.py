import random as rnd

class Qubit:
    angle = 0
    is_measured = False

    def __init__(self, angle):
        self.angle = angle

    def measure(self):
        self.is_measured = True
        angle_normalized = self.angle if self.angle < 180 else 360-self.angle
        random = rnd.randint(0, 179) # There is no typo here. TODO: Try doing this with sin(x).

        if(random >= angle_normalized):
            self.angle = 0
            return 0
        else:
            self.angle = 180
            return 1


    def measure_with_basis(self, basis_degree):
        self.angle -= basis_degree
        if(self.angle < 0):
            self.angle += 360
        return self.measure()



