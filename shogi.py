#!/usr/bin/python
# -*- coding: UTF-8 -*-

# Shogi
#
# A simple shogi game
#
# author: Clement Scheelfeldt Skau
# website: http://www.cs.au.dk/~u083430/
# last edited: May 2009

from math import floor, ceil, pi
import os, sys, random#, string
import socket, subprocess, threading
import gtk, cairo, glib

FONT_SIZE = 20
WIDTH = 600
HEIGHT = 600
PIECE_LABELS_DICT = {
  'p': {0:"歩",1:"と"}
, 'l': {0:"香",1:"成"}
, 'n': {0:"桂",1:"成"}
, 'b': {0:"角",1:"龍"}
, 'r': {0:"飛",1:"龍"}
, 's': {0:"銀",1:"成"}
, 'g': {0:"金"}
, 'k': {0:"王",1:"玉"}
#  'p': {0:"歩兵",1:"と金"}
#, 'l': {0:"香車",1:"成香"}
#, 'n': {0:"桂馬",1:"成桂"}
#, 'b': {0:"角行",1:"龍馬"}
#, 'r': {0:"飛車",1:"龍王"}
#, 's': {0:"銀将",1:"成銀"}
#, 'g': {0:"金将"}
#, 'k': {0:"王将",1:"玉将"}
}
PIECE_CHARS_BLACK = "PBRLNSGK"
PIECE_CHARS_WHITE = "pbrlnsgk"
PIECE_CHARS = PIECE_CHARS_WHITE+PIECE_CHARS_BLACK
EMPTY_CHARS = "-"

START_BOARD = '''
LNSGKGSNL
-R-----B-
PPPPPPPPP
---------
---------
---------
ppppppppp
-b-----r-
lnsgkgsnl
'''.strip()
BOARD_LETTERS = "abcdefghi"


class Model():

    def __init__(self):
        self.pieces = list()
        row,col = 1,1
        for c in START_BOARD:
            if c == '\n' or c == '\r':
                row += 1
                col = 1;
            elif c in PIECE_CHARS:
                self.pieces.append( (10-col,BOARD_LETTERS[row-1],c) )
                col += 1
            elif c in EMPTY_CHARS:
                col += 1
    
    
    def getPieces(self):
        return self.pieces
    
    
    def move(self,move):
        for (n,l,t) in self.pieces:
            try:
                if (n,l) == (int(move[0]),move[1]):
                    print "found: ",(move[2],move[3],t)
                    self.pieces.remove( (n,l,t) )
                    for (nn,nl,nt) in self.pieces: # remove captured piece
                        if (nn,nl) == (int(move[2]),move[3]):
                            self.pieces.remove( (nn,nl,nt) )
                            break
                    self.pieces.append( (int(move[2]),move[3],t) )
            except Exception as e:
                print "Exception: '%s' !" % e
                return




class Backend( threading.Thread ):
   
    def startUp(self):
        try:
            self.sock,self.childsock = socket.socketpair()
            self.gnushogi = subprocess.Popen(
                "gnushogi",
                shell=True,
                #env={"PYTHONUNBUFFERED":"t"},
                bufsize=-1,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                #stdout=self.childsock.fileno(),
                stderr=subprocess.STDOUT,
                close_fds=False,
                universal_newlines = True)
            self.sock.settimeout(0.3)
        except IOError:
            print "Exception: Error opening GNUShogi. Required as back-end engine!"
            exit(0)


    def run(self):
        self.data, self.move = "",False
        line = self.gnushogi.stdout.readline()
        while line:
            self.data += line
            print line
            line = self.gnushogi.stdout.readline()
            if self.move:
                if not line.startswith("Illegal move"):# and line.find(self.move) > 0:
                    print "I move:"+self.move
                    self.model.move(self.move)
                self.move = False
            else:
                if line.find(" ... ") > 0:
                    parts = line.split()
                    self.model.move(parts[2])
                    print "...",parts[2]
                else:
                    parts = line.split()
                    self.model.move(parts[1])

    
    
    def registerModel(self,model):
        self.model = model
    
    
    def registerBoard(self,board):
        self.board = board
        self.board.registerGNUShogi(self.gnushogi)


    def write(self,inp):
        try:
            self.gnushogi.stdin.write( inp+"\n" )
            self.gnushogi.stdin.flush()
        except:
            print "except"


    def read(self):
        return self.data
    
    
    def trymove(self,move):
        self.move = move
        self.write(move)



class Board(gtk.DrawingArea):

    def __init__(self):
        super(Board, self).__init__()
        
        self.model = Model()
        self.backend = Backend()
        self.backend.startUp()
        self.backend.registerModel(self.model)
        self.backend.registerBoard(self)
        self.backend.start()

        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0, 0, 0))
        self.set_size_request(WIDTH, HEIGHT)

        self.connect("expose-event", self.expose)
 
        self.init_game()


    def init_game(self):
        try:
            self.piece = cairo.ImageSurface.create_from_png("piece-blank-small.png")
            self.board = cairo.ImageSurface.create_from_png("board.png")
        except Exception, e:
            print "Exception: Error loading graphics\n", e
            sys.exit(1) # exit()?
        self.drag = False
        glib.timeout_add(200, self.on_timer)


    def on_timer(self):
        self.queue_draw()
        return True;


    def registerGNUShogi(self,gs):
        self.gs = gs

    
    def shogiToPixel(self,number,letter):
        if type(letter) is type("string"):
            letter = BOARD_LETTERS.find(letter)+1
        return (570-(number*60)), ((letter*60)-30)


    def pixelToShogi(self,x,y):
        n,l=0,0
        if x >= 30 and x <= 570 and y >= 30 and y <= 570:
            n,l = 9-floor((x-30)/60), floor((y-30)/60)+1
            l = BOARD_LETTERS[int(l)-1]
        return n,l


    def pixelToShogiPixel(self,x,y):
        n,l=self.pixelToShogi(x,y)
        return self.shogiToPixel(n,l)


    def expose(self, widget, event):
        cr = widget.window.cairo_create()
        
        # clear screen
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        
        # paint board
        cr.set_source_surface(self.board, 0, 0)
        cr.paint()
        
        if not self.drag:
            self.updateView()
        
        # paint pieces
        for ((x, y), t) in self.pieces:
#            cr.save()
#            cr.rotate(1)
            cr.set_source_surface(self.piece, x, y)
#            cr.restore()
            cr.paint()
            
            cr.select_font_face("Kanji Stroke Orders",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(FONT_SIZE)
            cr.move_to(x+(self.piece.get_width()-FONT_SIZE)/2,y+self.piece.get_height()-FONT_SIZE)
            if t == t.lower():
              cr.set_source_rgb(0.9, 0.1, 0.1)
            else:
              cr.set_source_rgb(0.1, 0.1, 0.1)
            if t.lower() in PIECE_LABELS_DICT:
                cr.show_text(PIECE_LABELS_DICT[t.lower()][0])
            else:
                cr.show_text(t)
        
        if self.drag:
            ((x,y),t),(ox,oy),(bx,by) = self.drag
            cr.set_source_surface(self.piece, x, y)
            cr.paint()
            
            cr.select_font_face("Kanji Stroke Orders",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(FONT_SIZE)
            cr.move_to(x+(self.piece.get_width()-FONT_SIZE)/2,y+self.piece.get_height()-FONT_SIZE)
            if t == t.lower():
              cr.set_source_rgb(0.9, 0.1, 0.1)
            else:
              cr.set_source_rgb(0.1, 0.1, 0.1)
            if t.lower() in PIECE_LABELS_DICT:
                cr.show_text(PIECE_LABELS_DICT[t.lower()][0])
            else:
                cr.show_text(t)
    
    
    def updateView(self):
        ps = self.model.getPieces()
        self.pieces = list()
        for (n,l,t) in ps:
            x,y = self.shogiToPixel(n,l)
            self.pieces.append( ((x,y),t) )

    def motion_notify_cb(self, event):
        if self.drag:
            ((x,y),t),(ox,oy),(bx,by) = self.drag
            self.drag = ((event.x-ox,event.y-oy),t),(ox,oy),(bx,by)
        
    def button_press_cb(self, event):
        if event.button == 1:
            en,el = self.pixelToShogi(event.x,event.y)
            if (en,el) != (0,0):
                for ((x,y),t) in self.pieces:
                    if self.pixelToShogi(x,y) == (en,el):
                        epx,epy = self.shogiToPixel(en,el)
                        ox,oy = event.x-epx,event.y-epy
                        self.pieces.remove( ((x,y),t) )
                        self.drag = ((x,y),t),(ox,oy),(x,y)

    def button_release_cb(self, event):
        if event.button == 1 and self.drag:
            ((x,y),t),(ox,oy),(bx,by) = self.drag
            (on,ol),(nn,nl) = self.pixelToShogi(bx,by),self.pixelToShogi(x+ox,y+oy)
            move = ("%d%c%d%c"%(on,ol,nn,nl))
            #self.backend.trymove(move)
            self.gs.stdin.write(move+"\n\n\n")
            self.gs.stdin.flush()
            self.pieces.append( (self.pixelToShogiPixel(bx,by),t) )
            self.drag = False


class Shogi(gtk.Window):

    def __init__(self):
        super(Shogi, self).__init__()
        
        self.set_title('Shogi')
        self.set_size_request(WIDTH, HEIGHT)
        self.set_resizable(False)
        self.set_position(gtk.WIN_POS_CENTER)

        self.board = Board()
        
        self.connect("button-press-event", self.button_press_cb)
        self.connect("button-release-event", self.button_release_cb)
        self.connect("motion-notify-event", self.motion_notify_cb)
        
        self.set_events(gtk.gdk.EXPOSURE_MASK
                | gtk.gdk.POINTER_MOTION_MASK
                | gtk.gdk.ENTER_NOTIFY_MASK
                | gtk.gdk.LEAVE_NOTIFY_MASK
                | gtk.gdk.BUTTON_PRESS_MASK
                | gtk.gdk.BUTTON_RELEASE_MASK
        )

        self.set_extension_events(gtk.gdk.EXTENSION_EVENTS_ALL)
        
        self.add(self.board)

        self.connect("destroy", gtk.main_quit)
        self.show_all()

    def motion_notify_cb(self, widget, event):
        self.board.motion_notify_cb(event)
        
    def button_press_cb(self, widget, event):
        self.board.button_press_cb(event)

    def button_release_cb(self, widget, event):
        self.board.button_release_cb(event)

Shogi()
gtk.main()
