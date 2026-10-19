"""One-shot macOS location request; only called by the user's location button."""
import threading
from Foundation import NSObject
from CoreLocation import CLLocationManager
from PyObjCTools import AppHelper

_lock=threading.Lock()

class JarvisLocationDelegate(NSObject):
 def locationManager_didUpdateLocations_(self,manager,locations):
  if not locations:return
  location=locations[-1]
  if location.horizontalAccuracy()<0:return
  c=location.coordinate();self.result={'latitude':float(c.latitude),'longitude':float(c.longitude)};self.done.set()
 def locationManager_didFailWithError_(self,manager,error):
  self.error='Не вдалося визначити розташування. Перевірте дозвіл геолокації або введіть місто.';self.done.set()
 def locationManagerDidChangeAuthorization_(self,manager):
  status=manager.authorizationStatus()
  if status in (3,4):manager.requestLocation()
  elif status in (1,2):self.error='Доступ до геолокації вимкнений. Введіть місто вручну.';self.done.set()

def locate():
 if not _lock.acquire(blocking=False):raise ValueError('Визначення місця вже триває.')
 try:
  delegate=JarvisLocationDelegate.alloc().init();delegate.done=threading.Event();delegate.result=None;delegate.error=None;delegate.manager=None
  def start():
   try:
    if delegate.done.is_set():return
    manager=CLLocationManager.alloc().init();delegate.manager=manager;manager.setDelegate_(delegate)
    manager.setDesiredAccuracy_(1000.)
    status=manager.authorizationStatus()
    if status in (3,4):manager.requestLocation()
    elif status in (1,2):delegate.error='Доступ до геолокації вимкнений. Введіть місто вручну.';delegate.done.set()
    else:manager.requestWhenInUseAuthorization()
   except Exception:delegate.error='Системна геолокація недоступна. Введіть місто вручну.';delegate.done.set()
  def cleanup():
   if delegate.manager:
    delegate.manager.stopUpdatingLocation();delegate.manager.setDelegate_(None);delegate.manager=None
  AppHelper.callAfter(start)
  try:
   if not delegate.done.wait(25):
    delegate.done.set();raise ValueError('Геолокація не відповіла. Перевірте дозвіл macOS або введіть місто.')
   if delegate.error:raise ValueError(delegate.error)
   if not delegate.result:raise ValueError('Місце не визначено.')
   return delegate.result
  finally:AppHelper.callAfter(cleanup)
 finally:_lock.release()
