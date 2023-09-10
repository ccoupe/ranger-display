from machine import Timer
import sh1106
import time
#import deja24
from sys import platform
class MessageDevice:
  '''
  Create a full screen window on a small LCD screen - tested with
  a sh1106 controller on esp32s2, pi pico w, 
  
  We have a 'device' and a 'canvas' that uses the devices.
  For micropython, timers are different.
  Timer 1 is the 5 minute screen blanking.
  
  Settings argument is an object from lib/Settings which parses the json file
  
  BareMessageDevice.display_text("text string") breaks the text into words 
  by whitespace and attempts to get the most number of words per line
  that will fit that line until the words are finished. It will then show
  those lines in the framebuffer. If the number of words is less than or equal
  to the number of lines on the display then the words are displayed on
  individual lines. 
  
  If there are more lines to display than framebuffer space allows then
  it will scroll additional lines in every second.
  
  After 5 minutes of no new messages the canvas will be cleared.
  There are some methods to change background and stroke colors and the
  current 'font' (one out of three predetermined sizes).
  
  Some arguments belong to Tk versions of this code. We don't use them
  for devices that use BareMessageDevice but we keep compatibility
  '''
  
  def __init__(self, config, tkwindow = None, tkclose = None, args=None):
    ##self.log = settings.log
    self.devFnt = None
    self.devLnH = 32
    self.config = config
    self.screen_height = 64
    self.screen_width = 120
    self.lnY = []
    self.font1 = config.get('Font1', None)
    self.font2 = config.get('Font2', None)
    self.font3 = config.get('Font3', None)
    self.viewPortW = None       # kind of best quess/max width
    self.devLns = 2				# number of lines on screen (depends on font)
    self.text_lines = []
    self.stroke_fill = ""       # color name
    self.background = None		#settings.background
    self.blank_minutes = 5
    self.scroll_timer = None
    self.blanking_timer = None
    self.cmdRun = None
    
    self.device = tkwindow
    self.screen_width = self.device.width
    self.screen_height = self.device.height
    self.canvas = tkclose 
    print(f'device: {self.screen_width} X {self.screen_height}')
    
    # Fonts and measurements
    # TODO: Much to do for micropyhon
    #self.font1 = ImageFont.truetype(settings.font1, settings.font1sz[0])
    #self.font2 = ImageFont.truetype(settings.font2, settings.font2sz[0])
    #self.font3 = ImageFont.truetype(settings.font2, settings.font3sz[0])
    '''
    self.font1 = font.Font(family=settings.font1, size=settings.font1sz[0])
    self.font2 = font.Font(family=settings.font2, size=settings.font2sz[0])
    self.font3 = font.Font(family=settings.font3, size=settings.font3sz[0])
    '''
    fnt = config.get('Font2', None)
    #self.stroke_fill = settings.stroke_fill
    #self.set_font(fnt)
    
    
  # 
  # ----------------- Visible (public)
  #
    
  def cmdOff(self, args):

    self.cmdRun = False
    self.log.info('cmdOff')
    self.device.hide()
    
  def cmdOn(self, args):

    self.cmdRun = True
    self.log.info('cmdOn')
    self.device.show()
  
  def display_text(self, payload):
    # should not have json for this call back
    if payload[0] == '{':
      self.log.warn("no json processed on text/set")
    #self.device.clear()
    self.device.sleep(False)
    self.device.fill(0)
    self.cmdRun = True
    words = payload.split()
    nwd = len(words)
    self.notify_timer(self.blank_minutes*60)
    #self.device.show()
    self.textLines = []
    if self.scroll_timer:
      self.scroll_timer.deinit()
      self.scroll_timer = None
      
    self.needscroll = self.layoutLines(self.textLines, self.devLns, nwd, words)
    if self.needscroll:
      # set 1 sec timer
      if platform == 'rp2': 
        self.scroll_timer = Timer(mode=Timer.PERIODIC, period=1000,
                                  callback=self.scroll_timer_fired)
      else:
        self.scroll_timer = Timer(2)
        Timer.init(self.scroll_timer, mode=Timer.PERIODIC, period=1000,
                                     callback=self.scroll_timer_fired)
     #print(f'setup scroll for {len(self.textLines)} lines')
      self.displayLines(0, self.devLns, self.textLines)
    else:
      #print("not scrolling")
      self.displayLines(0, self.devLns, self.textLines)
    self.device.show()
    
  # This will destroy and recreate font and writer classes/objects
  # TBD
  def set_font(self, fnt):
    if fnt == 2:
      self.devFnt = self.font2
      self.devLnH = self.settings.font2sz[1] # ex: 16
    elif fnt == 3:
      self.devFnt = self.font3
      self.devLnH = self.settings.font3sz[1] # ex: 21
    else:
      self.devFnt = self.font1 
      self.devLnH = self.settings.font1sz[1] # ex: 32
    self.devLns = int(self.device.height/self.devLnH)     # number of lines = device.height/Font_Height
    #self.log.info(f'devLnH: {self.devLnH}')
    #self.log.info(f'devLns: {self.devLns}={self.device.height}/{self.devLnH}')
    
  def set_stroke(self, color_str):
    #self.log.info(f"Setting stroke to {color_str}")
    self.stroke_fill = color_str
    
  def set_background(self, color_str):
    #self.log.info(f'Setting background to {color_str}')
    self.background = color_str
    self.canvas.configure(background=self.background)
    
  def set_timeout(self, tmo):
    #self.log.info(f"Setting blank time to {tmo}")
    self.blank_minutes = int(tmo)
    
  # --------- Private methods below ----------------------

  # returns True if we need to scroll 
  def layoutLines(self, lns, nln, nwd, words):
    lns.clear()
    #print(f'layoutlines: {nln} {nwd} {words}')
    if nwd <= nln:
      y = 0
      for wd in words:
        wid = self.canvas.stringlen(wd, False)
        #print(f"check width of {wd} is {wid}")
        lns.append(wd)
        y += self.devLnH
    else: 
        ln = ""
        wid = 0
        y = 0
        for wd in words:
          w = self.canvas.stringlen(' '+wd, False)
          if (wid + w) > self.device.width:
            lns.append(ln)
            wid = 0
            ln = ""
            y += self.devLnH
          if wid == 0:
            ln = wd
            wid = w
            #self.log.info(f'first word |{ln}|{wid}')
          else:
            ln = ln+' '+wd
            wid = self.canvas.stringlen(ln, False)
            #self.log.info(f'partial |{ln}|')

        # anything left over in ln ?
        if wid > 0:
          lns.append(ln)
      
    return len(lns) > nln


  # st is index (0 based), end 1 higher  
  def displayLines(self, st, end, textLines):
    self.firstLine = st
    self.device.fill(0)
    #print(f'dspL {st} {end}')
    if len(self.textLines) < end:
      end = len(self.textLines)
      print(f'fixing up end to {end}')
      
    #with canvas(self.device, dither=True) as draw:
    y = 0
    for i in range(st, end):
        wid = self.canvas.stringlen(self.textLines[i], False)
        x = int((self.device.width - wid)/2)
        #print(f"Line: {y}@{self.textLines[i]}")
        self.canvas.set_textpos(self.device, y, x)
        self.canvas.printstring(self.textLines[i])
        y += self.devLnH
    self.device.show()

  # need to track the top line # displayed: global firstLine, 0 based.
  def scroll_timer_fired(self, timer):
    #self.log.info(f'scroll firstLine: {firstLine}')
    self.firstLine = self.firstLine + self.devLns
    maxl = len(self.textLines)
    if self.firstLine > maxl:
      # at the end, roll over
      self.firstLine = 0
    end = min(self.firstLine + self.devLns, maxl)
    self.displayLines(self.firstLine, end, self.textLines)

  # no message for 5 minutes, stop the display and any scrolling
  def notify_timer_fired(self, timer):
    print('TMO fired')
    if self.scroll_timer:
        self.scroll_timer.deinit()
        self.scroll_timer = None
    # wait a bit, hope the scrolling stops
    time.sleep(1)
    self.device.fill(0)
    self.device.show()
  
  def notify_timer(self, secs):
    if self.blanking_timer:
      # reset unfired timer
      self.blanking_timer.deinit()
    if platform == 'rp2':
      self.blanking_timer = Timer(mode=Timer.ONE_SHOT, period=(secs*1000),
                                      callback=self.notify_timer_fired)
    else:
      self.blanking_timer = Timer(1)
      Timer.init(self.blanking_timer, mode=Timer.ONE_SHOT, period=(secs*1000),
                                      callback=self.notify_timer_fired)

  
