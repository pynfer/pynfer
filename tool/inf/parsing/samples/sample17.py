def rotate_tires( car ) :
   for i in range(1, car.tire_count()) :
       print ("Moving tire from " + str(i))
       car =
       car.set_tire( i+1 )
   print ("Moving tire from " + str(car.tire_count()))
   car.set_tire( 1 )

class Car(object) :
    def __init__(self) :
        self.number_of_tires = 4

    def set_tire( self, nPos ) :
        print ("Setting tire into position: " + str(nPos ))

    def tire_count(self) :
        return self.number_of_tires
        
class Hybrid(Car) :
    def __init__(self) :
        self.number_of_tires = 3

c = Car()
c.
rotate_tires(c)
h = Hybrid()
rotate_tires(h)
