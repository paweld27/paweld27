#####################################################
#                                                   #
#   VisToole - AsTeR - tech@asterlab.pl             #
#   Paweł Dorobek                                   #
#                                                   #
#   ver. 0.910      - 02.2024                       #
#                                                   #
#####################################################


import pandas as pd
import numpy as np
from matplotlib.widgets import Button, CheckButtons
import matplotlib.transforms as transforms
import matplotlib.pyplot as plt


class FIFO():
    def __init__(self, length, **kwargs):
        if length < 1:
            raise ValueError("'length' should be greater than 0")
        self._length = length
        err = 1
        if 'fifo' in kwargs:
            if isinstance(kwargs['fifo'], list):
                if len(kwargs['fifo']) ==  length:
                    self._fifo = kwargs['fifo']
                    err = 0
        if err:            
            self._fifo = [0 for i in range(length)]

        self.licz = -1
        if 'licz' in kwargs:
            if kwargs['licz'] == 'on':
                self.licz = 0


    def put(self, value):
        self._fifo.append(value)
        if self.licz >= 0:
            self.licz += 1
        return self._fifo.pop(0)

    @property
    def length(self):
        return self._length
        
    @property
    def fifo(self):
        return self._fifo

    def reset(self):
        self._fifo = [0 for i in range(self.length)]

    def res(self):
        self._fifo = [0 for i in range(self.length)]


class CBoxy():
    def __init__(self, boxy, **kwargs):
        self.boxy = boxy
        
        self._enabled = True
        self._visible = True
        self._addfunc = None
                        
        for (k, v) in kwargs.items():
            if '_'+k in self.__dict__:
                setattr(self, '_'+k, v)
                
        if not self._enabled:
            self._visible = False
  
    def _enable(func, *args, **kwargs):
        def inner(self, *args, **kwargs):
            if self._enabled:
                answer = func(self, *args, **kwargs)
            else:
                answer = 0
            return answer
        return inner

    def set_addfunc(self, func):
        self._addfunc = func

    @property
    def addfunc(self):
        return self._addfunc

    @addfunc.setter
    def addfunc(self, func):
        self.set_addfunc(func)

    @property
    def enable(self):
        return self._enabled

    @enable.setter
    def enable(self, ena):
        self._enabled = ena

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, vis):
        self._visible = vis

    def get_visible(self):
        return self._visible

    def get_present(self, bx):
        return self.boxy.loc[self.boxy['name'] == bx, 'present'].any()  
    
    def get(self, bx):
        return self.boxy.loc[self.boxy['name'] == bx, 'active'].any()

    def is_valid_bx_name(self, bx):
        return bx in self.boxy['name']

    def get_status(self):
        return self.boxy['active']

    def set(self, bx, val):
        self.boxy.loc[self.boxy[self.boxy['name'] == bx].index[0], 'active'] = val
    
    def get_label(self, bx):
        return self.boxy.loc[self.boxy['name'] == bx, 'label'].item()

    def __getattr__(self, bx):
        return self.get(bx)

#    def __setattr__(self, bx, val):
#        self.set(bx, val)


class CBoxy_mpl(CBoxy):
    """
    This is a CheckButtons maker for matplotlib

    mpl.CheckButtons uses visibility of crosslines as active status
    So hiding mpl.CheckButtons would clear its status.
    To untie status from cross visibility only values from
    boxy['active'] will be taken into consideration.
    self.on_click func will track only user activity
    and copy this to boxy['active']
    """
    def __init__(self, boxy, box_bounds, **kwargs):
        super().__init__(boxy, **kwargs)
        self.boxy = boxy[boxy['present'] == 1]
        self.boxy.reset_index(drop=True, inplace=True)

        self.fig = kwargs['fig']  # obligatory
        
        if 'box_props' in kwargs:
            box_props = kwargs['box_props']
        else:
            box_props = {}

        self.ax = self.fig.add_axes(box_bounds, **box_props)
        
        self.ax.set_visible(self._visible)
        self.ccbox = CheckButtons(
            ax=self.ax,
            labels=self.boxy['label'].tolist(),
            actives=self.boxy['active'].tolist(),
            frame_props=kwargs['frame_props'] if 'frame_props' in kwargs else None,
            check_props=kwargs['check_props'] if 'check_props' in kwargs else None
        )
        self.ccbox.on_clicked(self.on_clicked)

        self.cid = kwargs.get('cid', '')
        self._enabled = kwargs.get('enabled', True)

        if not self._visible:
            self.clear_all()

        self.box_move = MoveBox(fig=self.fig, ax=self.ax)
        self._pick_ev_id = self.fig.canvas.mpl_connect('pick_event', self._on_pick)
        self._click_ev_id = self.fig.canvas.mpl_connect('button_press_event',
                                                            self._on_click)


        self.zz = [c for c in self.ax.xaxis.get_children() if isinstance(c, plt.Text)]
        self.zz += [c for c in self.ax.yaxis.get_children() if isinstance(c, plt.Text)]
        self.zz.append(self.ax.title)


    def _on_click(self, event):
        """
        CBox on/off

        """
       
        if event.button == 3:
        
            if not any(map(lambda x: x.get_window_extent().contains(event.x,
                                                                    event.y)
                               and x.get_visible(), self.fig.axes + self.zz)):
                self.set_visible(not self.get_visible())
        self.fig.canvas.draw_idle()

            
    def _on_pick(self, event):
        """   pick handles function   """
    
        if event.mouseevent.button != 1:   #  left mouse button
            return

        """
        here we pick checkboxes 
        event.artist is the ax axes of the corresponding element
        """               # new moving CheckButtons and buttons
        if event.artist == self.ax: 
            # outer dimensions in disp points
            full_box = event.artist.get_window_extent()  
            # a little bit smaller box so that finnaly only edges will be responsive
            less_box   = event.artist.get_window_extent().expanded(0.9, 0.9)   
            if full_box.contains(event.mouseevent.x, event.mouseevent.y) and \
                not less_box.contains(event.mouseevent.x, event.mouseevent.y):
                self.box_move.drag(event)

    def get_bbox(self):  
        cx = self.ax.get_window_extent().get_points()  # disp
        box = transforms.Bbox(cx).transformed(self.fig.transFigure.inverted())  #ax
        return box   # BoxBase
                
    def on_clicked(self, event):
        """
        fired by mpl.ccbox.set_active() every time the crossline changes

        This func only keeps an eye on the 'xor' status
        and eventually adds additional addfunc at the end
        """
        status = self.ccbox.get_status()
        idx = [i for i, k in enumerate(self.boxy['active']) if k != status[i]]
        if len(idx) == 0:
            return
        idx = idx[0]
        ac = status[idx]
        acx = self.boxy.loc[idx, 'xor']
        if ac and acx != 0:
            """ list of others bx from group to off """
            ide = [i for i, k in enumerate(self.boxy['xor']) if i != idx and k == acx]
            lide = len(ide)
            if lide > 0:
                for i in range(lide):
                    self.clear(self.boxy.loc[ide[i], 'name'])
        self.get_status()  # uaktualnia boxy if self._visible
        if self._addfunc != None and self._visible:
            self._addfunc()
    
    def get_status(self):
        status = self.ccbox.get_status()
        if self._visible:
            self.boxy = self.boxy.assign(active = status)
        return status

    def set_active(self, idx):
        """
        1 - toggle status

        nazwa została ze względu na podobną w mpl
        self.boxy['active'] uaktualnia się w on_clicked
        po ccbox.set_active(idx) if self._visible
        """
        self.ccbox.set_active(idx)

    def clear_all(self):
        status = self.ccbox.get_status()
        idx = [i for i, k in enumerate(status) if k == True]
        for i in range(len(idx)):
            self.set_active(idx[i])               

    def clear(self, bx):
        """
        bx = 'pik_pik_bx'

        single box for now, used in on_clicked
        when 'xor' checking
        """
        status = self.ccbox.get_status()
        idx = self.boxy[self.boxy['name'] == bx].index
        if len(idx) == 0:
            return
        idx = idx[0]
        if status[idx] == True:
            self.ccbox.set_active(idx)

    def set(self, bx):
        """
        bx = 'pik_pik_bx'

        single box for now
        """
        status = self.ccbox.get_status()
        idx = self.boxy[self.boxy['name'] == bx].index
        if len(idx) == 0:
            return
        idx = idx[0]
        if status[idx] == False:
            self.ccbox.set_active(idx)

            
    @CBoxy._enable
    def set_visible(self, vis):#, color):
        """
        takes status from boxy['active']

        """
        if self._visible == vis:
            return
        self._visible = vis
        if vis == False:
            self.clear_all()
            self.ax.set_visible(vis)
        else:
            """   list of bx's to recover   """ 
            idx = [i for i, k in enumerate(self.boxy['active']) if k == True]
            for i in range(len(idx)):
                self.ccbox.set_active(idx[i])
            self.ax.set_visible(vis)

            
    @CBoxy.visible.setter      # @CBoxy zeby odziedziczyc @property
    def visible(self, vis):
        self.set_visible(vis)

###      /\/\/\ CBoxy  /\/\/\   #####


###      \/\/\/ Move   \/\/\/   #####


class TopVistoole():
    def __init__(self, **kwargs):
        self._addfunc = None
        self._prefunc = None

        if 'addfunc' in kwargs:
            self.set_addfunc(kwargs['addfunc'])

        if 'prefunc' in kwargs:
            self.set_prefunc(kwargs['prefunc'])

    def set_prefunc(self, func):
        self._prefunc = func

    @property
    def prefunc(self):
        return self._prefunc

    @prefunc.setter
    def prefunc(self, func):
        self.set_prefunc(func)


    def set_addfunc(self, func):
        self._addfunc = func

    @property
    def addfunc(self):
        return self._addfunc

    @addfunc.setter
    def addfunc(self, func):
        self.set_addfunc(func)
  

class MoveXY(TopVistoole):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.follower = 0
        self.releaser = 0
        self.is_move = False
        self.xy = [0, 0]    # old mouse position
        self.xonly = False
        self.yonly = False
        self.fig = None
        self.ax = None
        
        for (k, v) in kwargs.items():
            if k in self.__dict__:
                setattr(self, k, v)

    def drag(self, event, obj=None, xonly=False, yonly=False, **kwargs):
        if obj != None:
            self.obj = obj
        else:
            self.obj = event.artist
        for (k, v) in kwargs.items():
            if k in self.__dict__:
                setattr(self, k, v)

        if self.fig == None:
            self.fig = getattr(self, 'fig0')
        if self.ax == None:
            self.ax0 = getattr(self, 'ax0')
        if self.fig == None or self.ax == None:
            raise ValueError("'fig' or 'ax' == 'None'")            
        self.xonly = xonly
        self.yonly = yonly
        if self.xonly and self.yonly:
            raise ValueError("'xonly' and 'yonly' can't be both eq 'True'")
        self.xstart, self.ystart = self._get_position()
        self.transOrygin = self.ax.transAxes
        if self.obj in self.fig.get_children():
            self.transOrygin = self.fig.transFigure
        self.xy = self.transOrygin.inverted().transform((event.mouseevent.x,
                                                         event.mouseevent.y))
        self.follower = self.fig.canvas.mpl_connect("motion_notify_event", self._make_drag)
        self.releaser = self.fig.canvas.mpl_connect("button_release_event", self._stop)
        self.is_move = True
        if self._prefunc != None:
            self._prefunc()


    def _get_position(self):
        return self.obj.get_position()

    def _set_position(self, new_x, new_y):
        self.obj.set(x=self.xstart if self.yonly else new_x,
                     y=self.ystart if self.xonly else new_y)    

    def _make_drag(self, event):
        """
        ta funkcja korzysta ze wsp. disp event.x, event.y

        nie nadaje się do kursora, który korzysta ze wsp. data event.data, event.data 
        """
        pos_xy = self.transOrygin.inverted().transform((event.x, event.y))   # obecna mysza w orygin (ax/fig)
        xy0 = self._get_position()  
            
        new_x = xy0[0] + (pos_xy[0] - self.xy[0]) # - ile sie ruszyla mysza w x
        new_y = xy0[1] + pos_xy[1] - self.xy[1]
        
        self._set_position(new_x, new_y)      #  lewy-dolny róg textu
        self.xy = pos_xy
        
        if self._addfunc != None:
            self._addfunc()

        self.fig.canvas.draw()
     #   self.fig.canvas.draw_idle()
     #   self.fig.canvas.flush_events() 

    def _stop(self, event):
        self.fig.canvas.mpl_disconnect(self.releaser)
        self.fig.canvas.mpl_disconnect(self.follower)
        self.is_move = False
        

class MoveBox(MoveXY):

    def drag(self, event, obj=None, xonly=False, yonly=False, **kwargs):
        super().drag(event, obj, xonly=xonly, yonly=yonly, **kwargs)
        self.dxy = self.obj.get_position().bounds[2:]  # bounds  # (x, y, w, h)
 
    def _get_position(self):
        return self.obj.get_position().get_points()[0] # ((xmin, ymin), (xmax, ymax))

    def _set_position(self, new_x, new_y):
        self.obj.set_position([self.xstart if self.yonly else new_x,
                               self.ystart if self.xonly else new_y,
                               self.dxy[0], self.dxy[1]])



class Move1Curr(MoveXY):
    """
    1 cursor class definition

    'up'/'left' - use interchangeably
    """
    def __init__(self, cxy, pos, label, labup='down',
                 pick_event='on', **kwargs):
        super().__init__()
        x_pos = [0.04, 0.96]
        y_pos = [0.03, 0.97]

        if labup in ['up', 'right']:
            labup = 'up'
        else:
            labup = 'down'
        
        self.line_prop = dict(lw=1.5, ls='--', visible=True,
                              picker=True, pickradius=5, zorder=3)

        label_box = dict(facecolor='white', alpha=0.9, edgecolor='white')
        self.label_prop = dict(ha='center', bbox=label_box,
                picker=True, fontsize=10, fontweight='normal', visible=True)
        
        self.cxy = cxy
        self.cid = ''
        self.xonly = True
        self.yonly = True
        self.on_pick_button = 1
        self._visible = True
        self.ax = None
        self.fig = None
        for (k, v) in kwargs.items():
            if k in self.__dict__:
                setattr(self, k, v)

        if self.label_prop.get('label', 'N/A') != 'N/A':
            label = self.label_prop['label']
            self.label_prop.pop('label')
        
        if self.label_prop.get('bbox', 'N/A') in ['N/A', None]:
            self.label_prop['bbox'] = label_box
                                
        if self.cxy == 'x':
            self.yonly = False
            if not any(map(lambda x: x in self.line_prop.keys(), ['c', 'color'])):
                self.line_prop['c']  = 'blue'
            if not any(map(lambda x: x in self.label_prop.keys(), ['c', 'color'])):
                self.label_prop['c'] = 'blue'
            
            self.line = self.ax.axvline(x=pos, **self.line_prop)

            trans = transforms.blended_transform_factory(self.ax.transData,
                                                         self.ax.transAxes)
            self._lpos = x_pos

            self.label_prop['transform'] = trans
            pos_lab = self._lpos[1] if labup in ['up', 'right'] else self._lpos[0]
            self.label = self.ax.text(pos, pos_lab, label, **self.label_prop)
        else:
            self.xonly = False
            if not any(map(lambda x: x in self.line_prop.keys(), ['c', 'color'])):
                self.line_prop['c']  = '#ff0080'
            if not any(map(lambda x: x in self.label_prop.keys(), ['c', 'color'])):
                self.label_prop['c'] = '#ff0080'

            self.line = self.ax.axhline(y=pos, **self.line_prop)

            trans = transforms.blended_transform_factory(self.ax.transAxes,
                                                         self.ax.transData)
            self._lpos = y_pos

            self.label_prop['transform'] = trans
            pos_lab = self._lpos[1] if labup in ['up', 'right'] else self._lpos[0]
            self.label = self.ax.text(pos_lab, pos, label, **self.label_prop)

        if self.xonly and self.yonly:
            raise RuntimeWarning("'xonly' and 'yonly' can't be both eq 'True'")

        # because there is such a property 
        if 'visible' in kwargs:
            self.set_visible(kwargs['visible'])

        self._pick_ev_id = None
        if pick_event == 'on':
            self._pick_ev_id = self.fig.canvas.mpl_connect('pick_event', self._on_pick)

    def _on_pick(self, event):
        if self.on_pick_button == 1:
            if event.artist == self.line:
                self.drag(event)

    def set_on_pick(self, val):
        if val:
            self._pick_ev_id = self.fig.canvas.mpl_connect('pick_event', self._on_pick)
        else:
            self.fig.canvas.mpl_disconnect(self._pick_ev_id)
            self._pick_ev_id = None
        
    @property
    def in_win(self):
        """  False if not both in win   """
        if self.cxy == 'x':
            xs, xe = self.ax.get_xlim()
        else:
            xs, xe = self.ax.get_ylim()
        is_in = False
        if self._visible:
            if xs <= self.x <= xe:
                is_in = True
        return is_in


    def set_label_bbox(self, dikt):
        self.label.set_bbox(dikt)

    @property    
    def artist(self):
        """   alias .line   """
        return self.line

    @property
    def lpos(self):
        return self._lpos

    @property
    def visible(self):
        return self._visible

    def set_visible(self, vis):
        self.line.set(visible = vis)
        self.label.set(visible = vis)
        self._visible = vis
        self.fig.canvas.draw_idle()

    @visible.setter
    def visible(self, vis):
        self.set_visible(vis)

    def get_visible(self):
        return self._visible
         
    @property
    def dx(self):
        return self.dxy[0]

    @property
    def dy(self):
        return self.dxy[1]
   
    def drag(self, event, **kwargs):        
        for (k, v) in kwargs.items():
            if k in self.__dict__:
                setattr(self, k, v)
        
        self.follower = self.fig.canvas.mpl_connect("motion_notify_event", self._make_drag)
        self.releaser = self.fig.canvas.mpl_connect("button_release_event", self._stop)
        self.is_move = True
        if self._prefunc != None:
            self._prefunc(self)

        
    def _make_drag(self, event):

        # out of axis
        if event.xdata == None or event.ydata == None:
            return

        x, y = event.xdata, event.ydata
        self._set_position(x, y)  # uwzględnia razem
        
        if self._addfunc != None:
            self._addfunc(self)
        """ this can also be in addfunc """
        self.fig.canvas.draw()


    def get_position(self):
        if self.xonly:
            self.xy = self.line.get_xdata()
        if self.yonly:
            self.xy = self.line.get_ydata()
        return self.xy

    @property
    def x(self):
        return self.get_position()[0]
        
    @property
    def y(self):
        return self.get_position()[0]

    @x.setter
    def x(self, value):
        """    single cursor   """
        self.set_position(value)

    @x.setter
    def y(self, value):
        """    single cursor   """
        self.set_position(value)
    

    def set_position(self, value):
        """    single cursor   """
        self._set_position(value, value)
        

    def _set_position(self, x, y):
        if not self.yonly:
            self.line.set_xdata([x])
            self.label.set(x=x)
        if not self.xonly:
            self.line.set_ydata([y])
            self.label.set(y=y)



class Move2Curr(MoveXY):
    """
    1 cursor class definition

    'up'/'left' - use interchangeably
    this version offers only the same line and label properties
    for both cursors
    And that's what the fork is for.
    """
    def __init__(self, cxy, lab1, lab2, pos1=None, pos2=None, razem=False,
                 labup='down', pick_event='on', buttons=False, **kwargs):
        super().__init__(**kwargs)
        x_pos = [0.04, 0.96]
        y_pos = [0.03, 0.97]
        
        self.line_prop = dict(lw=1.5, ls='--', visible=True,
                              picker=True, pickradius=5, zorder=3)

        label_box = dict(facecolor='white', alpha=0.9, edgecolor='white')
        self.label_prop = dict(ha='center', bbox=label_box,
                picker=True, fontsize=10, fontweight='normal', visible=True)
        
        self.cxy = cxy
        self.cid1 = '1'
        self.cid2 = '2'
        self.xonly = True
        self.yonly = True
        if self.cxy == 'x':
            self.yonly = False
        else:
            self.xonly = False
        self.on_pick_button = 1
        self._visible = True
        self.toggle_vis = True
        self.buttons = buttons
        self.razem = razem  
        self.ax = None            # obligatory in kwargs: ax=ax
        self.fig = None           # obligatory in kwargs: fig=fig
        for (k, v) in kwargs.items():
            if k in self.__dict__:
                setattr(self, k, v)

        if kwargs.get('cid1', 'N/A') != 'N/A':
            kwargs.pop('cid1')

        if kwargs.get('cid2', 'N/A') != 'N/A':
            kwargs.pop('cid2')

        kwargs['labup'] = labup
            
        if self.label_prop.get('label', 'N/A') != 'N/A':
            label = self.label_prop['label']
            self.label_prop.pop('label')
        
        if self.label_prop.get('bbox', 'N/A') in ['N/A', None]:
            self.label_prop['bbox'] = label_box
                                
        self.c1 = Move1Curr(cxy, 0, lab1, cid=self.cid1, **kwargs)       
        self.c2 = Move1Curr(cxy, 0, lab2, cid=self.cid2, **kwargs)

        x1, x2, _, _ = self.sro4cur(self.c1)

        if self.cxy == 'x':
            self.c1.x = x1
            self.c2.x = x2
        else:
            self.c1.y = x2
            self.c2.y = x1

        self.dxy = 0
        
        self.c1.set_prefunc(self.__prefunc)
        self.c2.set_prefunc(self.__prefunc)


        self.c1.set_addfunc(self.__addfunc)
        self.c2.set_addfunc(self.__addfunc)

        self._pick_ev_id = None
        if pick_event == 'on':
            self._pick_ev_id = self.fig.canvas.mpl_connect('pick_event', self._on_pick)

    
        """
        oscilloscope like indicator

        for signal pre-processing
        """
        oscx_pos = (0.02, 0.91)
        oscy_pos = (0.39, 0.91)
        osc_pos = oscx_pos if self.cxy == 'x' else oscy_pos

        osc_box_prop = dict(facecolor='white', alpha=0.9,
                        edgecolor='blue' if self.cxy == 'x' else 'red')
        osc_text_ln1 =   "x1 =        , ∆x =        "
        osc_text_ln2 = "\nx2 =        , [―][―]  >||<"

        osc_text = osc_text_ln1 + osc_text_ln2

        self.oscillo = self.ax.text(*osc_pos, osc_text, color='black', fontsize=10,
                           bbox=osc_box_prop, visible=True, picker=True, zorder=8,
                           transform=self.ax.transAxes)
        self.update_osc()

        """
        oscilloscope on/off buttons


        """
        if self.cxy == 'x':
            osc_butt_pos = (0.7, 0.9, 0.08, 0.05)
            color = '#3498DB'
            hovercolor='blue'
            label = 'Xon/Xoff'
            osc_lab_prop = dict(color='#FFFFFF', fontsize='small',
                                fontweight='bold') 
        else:
            osc_butt_pos = (0.8, 0.9, 0.08, 0.05)
            color = '#ff44a2'
            hovercolor='red'
            label = 'Yon/Yoff'
            osc_lab_prop = dict(color='white', fontsize='small',
                                fontweight='bold')

        if self.buttons:
            self.ax_butt = self.fig.add_axes(osc_butt_pos, picker=True)
            self.button = Button(self.ax_butt, label, color=color,
                                 hovercolor=hovercolor)
            self.button.label.set(**osc_lab_prop)
            self.butt_id = self.button.on_clicked(self.toggle_visible)
        

            self._pick_ev_id = self.fig.canvas.mpl_connect('pick_event',
                                                           self._on_pick)

            self._click_ev_id = self.fig.canvas.mpl_connect('button_press_event',
                                                            self._on_click)

            self.butt_move = MoveBox(fig=self.fig, ax=self.ax)
            

        self.kbd_ev_id = self.fig.canvas.mpl_connect('key_press_event',
                                                    self.key_press)

            

        self.zz = [c for c in self.ax.xaxis.get_children() if isinstance(c, plt.Text)]
        self.zz += [c for c in self.ax.yaxis.get_children() if isinstance(c, plt.Text)]
        self.zz.append(self.ax.title)

        # because there is such a property 
        if 'visible' in kwargs:
            self.visible = kwargs['visible']

        


    def _on_click(self, event):
        """
        Oscillo buttons on/off

        """
       
        if event.button == 3:
        
            if not any(map(lambda x: x.get_window_extent().contains(event.x,
                                                                    event.y)
                               and x.get_visible(), self.fig.axes + self.zz)):
                self.ax_butt.set_visible(not self.ax_butt.get_visible())
        self.fig.canvas.draw_idle()


    def key_press(self, event):
        if event.key in ['a', 'A']:
            if self.buttons:
                self.ax_butt.set_visible(not self.ax_butt.get_visible())
            elif self.toggle_vis:
                self.toggle_visible()
            self.fig.canvas.draw_idle()
        return

    def update_osc(self):
        dt = self.c2.x - self.c1.x
        if self.cxy == 'x':
            x = 'x'
        else:
            x = 'y'
            dt = -dt
        fmt_t = "{:.4f}"
        num_x1 = fmt_t.format(self.c1.x)
        num_x2 = fmt_t.format(self.c2.x)
        num_dt = fmt_t.format(dt)
        osc_ln1 = x+"1 = "+num_x1+"    ∆"+x+" = " + num_dt
        osc_ln2 = x+"2 = "+num_x2
        if self.razem:
            osc_ln2 += '      [══]       >||<'
        else:
            osc_ln2 += '      [―][―]    >||<'
        self.oscillo.set(text = osc_ln1 + '\n' + osc_ln2)

        
    def __prefunc(self, obj):
        if obj == self.c1:
            self.dxy = obj.x - self.c2.x
        else:
            self.dxy = obj.x - self.c1.x
            
    def __addfunc(self, obj):
        if obj == self.c1:
            cur2 = self.c2
        else:
            cur2 = self.c1
        if self._razem:
            cur2.x = obj.x - self.dxy
        self.update_osc()
        if self._addfunc != None:
            self._addfunc()
 
        
    def _on_pick(self, event):
        
        """   pick handles function   """

        """
        here we pick buttons 
        event.artist is the ax axis of the corresponding button
        """               
        if event.mouseevent.button == 3:   #  right mouse button
        
            """
            here we pick buttons 
            event.artist is the ax axes of the corresponding button
            """

            if self.buttons:
                if event.artist == self.ax_butt:
                    self.butt_move.drag(event)
                return
            

            """
            Here we pick icons in oscilloX window
            event.artist is the oscillo text
            We have to check what icon was picked
            How it's done and why - look at transforms.py source file in main
            matplotlib folder and of course READ_the_DOC !!!
            """
            if event.artist == self.oscillo:
                osc_box = event.artist.get_bbox_patch().get_extents()
                x_norm = (event.mouseevent.x - osc_box.x0) / osc_box.width
                y_norm = (event.mouseevent.y - osc_box.y0) / osc_box.height
                if y_norm < 0.5:
                    if x_norm > 0.5:
                        if x_norm > 0.8:
                            self.center = True      
                        else:
                            self.razem = not self.razem
                            self.update_osc()
                        self.fig.canvas.draw()
            
    
        if event.mouseevent.button != 1:   #  left mouse button
            return

        if event.artist == self.oscillo:
            self.drag(event)
            return



    def set_on_pick(self, val):
        if val:
            self._pick_ev_id = self.fig.canvas.mpl_connect('pick_event', self._on_pick)
        else:
            self.fig.canvas.mpl_disconnect(self._pick_ev_id)
            self._pick_ev_id = None

    @staticmethod
    def sro4cur(cur):
        """
        Returns cursors positions close to the center of the plot

        in the curr ax space
        10% from the center of plot for y-cursor and 5% for x-cursor

        Usage
        -----
        x1, x2, _, _ = sro4cur('x')
        y2, y1, _, _ = sro4cur('y') 

        """
        if cur.cxy == 'x':
            dr = 0.05
            limes = cur.ax.get_xlim()
        else:
            limes = cur.ax.get_ylim()
            dr = 0.1
        xs = limes[0]
        xe = limes[1]
        xr = xe - xs
        xm = xs + xr / 2
        x1 = xm - xr * dr
        x2 = xm + xr * dr
        return x1, x2, xs, xe

    @property
    def center(self):
        return False

    @center.setter
    def center(self, value):
        x1, x2, _, _ = self.sro4cur(self.c1)
        if self.c1.cxy == 'x':
            self.c1.x = x1
            self.c2.x = x2
        else:
            self.c1.y = x2
            self.c2.y = x1


    @property
    def in_win(self):
        """  False if not both in win   """
        return self.c1.in_win and self.c1.in_win


    def set_label_bbox(self, dikt):
        self.label.set_bbox(dikt)

    @property    
    def artist(self):
        """   alias .line   """
        return self.line

    @property
    def lpos(self):
        return self._lpos

    @property
    def visible(self):
        return self._visible

    def set_visible(self, vis):
        self.c1.visible = vis
        self.c2.visible = vis
        self.oscillo.set(visible = vis)
        self._visible = vis
        self.fig.canvas.draw_idle()

    def toggle_visible(self):
        self.set_visible(not self.visible)

    @visible.setter
    def visible(self, vis):
        self.set_visible(vis)

    def get_visible(self):
        return self._visible

    @property
    def razem(self):
        return self._razem

    @razem.setter
    def razem(self, value):
        self._razem = value if value in [True, False, 0 ,1] else False
    
    @property
    def dx(self):
        return self.dxy[0]

    @property
    def dy(self):
        return self.dxy[1]
         
    @property
    def dx(self):
        return self.dxy[0]

    @property
    def dy(self):
        return self.dxy[1]


class LegView(TopVistoole):
    """
    Interactive legend

    
    """
    def __init__(self, **kwargs):
        self.ax = 0
        self.fig = 0
        self.leg_addfunc = None
        self.leg_draggable = False

        for (k, v) in kwargs.items():
            if k in self.__dict__:
                setattr(self, k, v)

        self.set_addfunc(self.leg_addfunc)

        #             ax_line      leg_line     leg_label    ax_line      ax_line
        #             alpha        alpha        alpha        linewidth    zorder
        self.normal = dict(ax_la = 0.8, lg_la = 1,   lg_ba = 1,   ax_lw = 1.5)
        self.active = dict(ax_la = 1,   lg_la = 1,   lg_ba = 1,   ax_lw = 1.7, ax_zr = 2.5)
        self.passiv = dict(ax_la = 0.2, lg_la = 0.5, lg_ba = 0.6, ax_lw = 1.7, ax_zr = 2)

        self.legend = self.ax.legend(loc='upper right', edgecolor='black',
                                     draggable=self.leg_draggable)

        self.legend.get_frame().set(picker=True)
        
        self.leg_lines = self.legend.get_lines()   # lines in legend
        self.leg_labels = self.legend.get_texts()  # legend labels
        self.sig_labels = list(map(lambda x: x.get_text(), self.leg_labels))
        self.ax_lines = [x for x in self.ax.get_children()
                         if x.get_label() in self.sig_labels]

        self.artists = {}
        for i, k in enumerate(self.leg_labels):
            self.artists[self.leg_labels[i]] = [self.ax_lines[i], self.leg_lines[i],
                                                self.leg_labels[i]]
            self.leg_labels[i].set_picker(True)  #  they will respond when it's label is picked

        self.back_view()

        self._pick_ev_id = self.fig.canvas.mpl_connect('pick_event',
                                                        self._on_pick)

        self._click_ev_id = self.fig.canvas.mpl_connect('button_press_event',
                                                        self._on_click)

        self.on_hov_id = self.fig.canvas.mpl_connect('motion_notify_event', self._on_hover)

        self.fig_ev_id = self.fig.canvas.mpl_connect('figure_leave_event', self.fig_leave)

        self.zz = [c for c in self.ax.xaxis.get_children() if isinstance(c, plt.Text)]
        self.zz += [c for c in self.ax.yaxis.get_children() if isinstance(c, plt.Text)]
        self.zz.append(self.ax.title)
        self.zz.append(self.legend)




    @staticmethod
    def pan_zoom_off():
        tb = plt.get_current_fig_manager().toolbar
        if 'pan' in tb.mode:  # query about 'pan' should be before 'zoom'
            tb.pan()
        if 'zoom' in tb.mode:
            tb.zoom()

    def fig_leave(self, event):
        self.legend.shadow = False
        self.legend.set_draggable(False)
        self.fig.canvas.draw_idle()
        

    def _on_hover(self, event):
        if self.legend.get_window_extent().contains(event.x,event.y):
            self.pan_zoom_off()
            self.fig.canvas.draw_idle()


    def _on_click(self, event):

        #zz = [ax_title, x_label, y_label, legend]

        if event.button == 1:
    
            if not any(map(lambda x: x.get_window_extent().contains(event.x,
                                                                    event.y)
                                and x.get_visible(), self.fig.axes + self.zz)):
                self.back_view()


    def _on_pick(self, event):
        if event.mouseevent.button == 1:
            if event.artist in self.leg_labels: 
                self.leg_on_pick(event)
                
            if event.artist == self.legend.get_frame():
                leg_box = self.legend.get_frame().get_bbox()
                lvl_box = leg_box.expanded(0.95, 0.95)
                if leg_box.contains(event.mouseevent.x, event.mouseevent.y) and \
                    not lvl_box.contains(event.mouseevent.x, event.mouseevent.y):
                    self.legend_move()


    def legend_move(self):
        self.legend.set_draggable(True)
        self.legend.shadow = True           
        self.fig.canvas.draw_idle()


    def leg_on_pick(self, event):
        for item in self.leg_labels:
            if item == event.artist:            # leg_label picked
                self.artists[item][0].set_linewidth(self.active['ax_lw'])   # ax_line
                self.artists[item][0].set_zorder(self.active['ax_zr'])
                self.artists[item][0].set_alpha(self.active['ax_la'])
                self.artists[item][1].set_alpha(self.active['lg_la'])     # leg_line
                self.artists[item][2].set_alpha(self.active['lg_ba'])     # leg_label
                
                if self._addfunc != None:
                    self._addfunc(item)

            else:                     # every other artist but not that picked
                self.artists[item][0].set_alpha(self.passiv['ax_la'])
                self.artists[item][0].set_zorder(self.passiv['ax_zr'])
                self.artists[item][1].set_alpha(self.passiv['lg_la'])   
                self.artists[item][2].set_alpha(self.passiv['lg_ba'])   
        self.fig.canvas.draw_idle()

    def back_view(self):
        for item in self.leg_labels:
            self.artists[item][0].set_alpha(self.normal['ax_la'])
            self.artists[item][0].set_linewidth(self.normal['ax_lw'])
            self.artists[item][1].set_alpha(self.normal['lg_la'])  
            self.artists[item][2].set_alpha(self.normal['lg_ba'])
            self.fig.canvas.draw_idle()

    

def Vistoole(toolsy, **kwargs):
    """
    toolsy='xbyb'

    fig=fig, ax=ax - obligatory when call
    """

    def vis_on_pick(event):
        if event.mouseevent.button != 1:   #  left mouse button
            return

        if event.artist in zz:
            vis_move.drag(event)
        return


    def toggle_visible(event):
        if event.key in ['a', 'A']:
            if cXX.visible ^ cYY.visible:
                cXX.set_visible(True)
                cYY.set_visible(True)
            else:
                cXX.set_visible(not cXX.visible)
                cYY.set_visible(not cYY.visible)


    cXX = cYY = cBB = legV = 0
    plot_dict = dict(fig = 'fig', ax = 'ax', toggle_vis=False)
    leg_dict = dict(fig = 'fig', ax = 'ax', leg_addfunc = None)
    
    for (k, v) in kwargs.items():
        if k in plot_dict:
            plot_dict[k] = v
        if k in leg_dict:
            leg_dict[k] = v

    fig = plot_dict['fig']
    ax = plot_dict['ax']

    if 'x' in toolsy:
        buttons = False
        if 'xb' in toolsy:
            buttons = True
        cXX = Move2Curr('x', 'x1', 'x2', **plot_dict, buttons=buttons)
        
    if 'y' in toolsy:
        buttons = False
        if 'yb' in toolsy:
             buttons = True
        cYY = Move2Curr('y', 'y1', 'y2', **plot_dict, buttons=buttons)

    if 'leg' in toolsy:
        legV = LegView(**leg_dict)

    if 'tm' in toolsy:        
        if 'tm' in kwargs:
            zz = kwargs['tm']
            zz = [c for c in zz if isinstance(c, plt.Text)]
        else:
            zz = []
        
        ax_title = ax.set_title(ax.title.get_text(), x=0.5, y=1)
        
        x_label = ax.set_xlabel(ax.get_xlabel())
        ax.xaxis.set_label_coords(0.5, -0.075)
        
        y_label = ax.set_ylabel(ax.get_ylabel())
        ax.yaxis.set_label_coords(-0.05, 0.5)
        
        zz += [ax_title, x_label, y_label]
        for v in zz:
            v.set_picker(True)

        vis_move = MoveXY(**plot_dict)
        vis_pick_ev_id = fig.canvas.mpl_connect('pick_event',
                                                vis_on_pick)

        kbd_ev_id = fig.canvas.mpl_connect('key_press_event',
                                            toggle_visible)
    
    return cXX, cYY, cBB, legV


####################       end of Vistoole module    ###########################

################################################################################
####################                      ######################################
####################   Example of use     ######################################


if __name__ == "__main__":
    import sys

###############################################################################
######                                                                   ######
######                fig, ax  should be obtained first                  ######

    fig, ax = plt.subplots(num='Main')


####################   CheckButton example             ########################

    boxy1 = pd.DataFrame(
        columns=
        [ 'present', 'active', 'xor', 'name',       'label'            ],
        data= [
        [ 1,         0,        1,     'rms_bx',     'RMS'              ],
        [ 1,         0,        1,     'std_bx',     'r\u2009m\u2009s≈' ],
        [ 1,         0,        1,     'mean_bx',    'mean'             ],
        [ 1,         0,        0,     'integr_bx',  'integr'           ],
        [ 1,         0,        0,     'lin_fit_bx', 'lin-fit'          ],
        [ 1,         0,        2,     'pik_pik_bx', 'pik-pik'          ],
        [ 1,         0,        2,     'tik_tik_bx', 'tik-tik'          ],
        [ 1,         0,        0,     'fft_db_bx',  'fft-dB'           ],
        [ 1,         0,        0,     'histN_bx',   'histN'            ],
        [ 0,         0,        0,     'histR_bx',   'histR'            ],
        ])


    cbox1 = CBoxy_mpl(boxy1, [0.89, 0.175, 0.10, 0.28],
                  fig=fig, cid='cb',
                  box_props=dict(facecolor='papayawhip', picker=True),
                  frame_props=dict(facecolor='papayawhip'),
                  check_props=dict(facecolor='black'))


    # second box after choosing tik-tik from the first one
    boxy_level = pd.DataFrame(
        columns=
        [ 'present', 'active', 'xor', 'name',     'label'   ],
        data= [
        [ 1,         1,        1,     'y2x',      'Y -> X'  ],
        [ 1,         0,        1,     'x2y',      'X -> Y'  ],
        [ 0,         0,        2,     'Level_21', 'Lv 2 - ʃ'],
        [ 0,         1,        2,     'Level_20', 'Lv 2 - ʅ'],
        ])


    lvbox = CBoxy_mpl(boxy_level, [0.775, 0.175, 0.10, 0.10],
                  fig=fig, cid='lv', enabled=False,  
                  box_props=dict(facecolor='beige', picker=True),
                  frame_props=dict(facecolor='beige'),
                  check_props=dict(facecolor='black'))


    def x2y_func():
        if lvbox.x2y:
            cYY.visible = True

    lvbox.set_addfunc(x2y_func)

    def ixy_on_off():
        if cbox1.tik_tik_bx:
            lvbox.enable = True
            lvbox.set_visible(True)
            if not(lvbox.x2y or lvbox.y2x):
                lvbox.set('y2x')
            if lvbox.x2y:
                cYY.visible = True
        else:
            lvbox.set_visible(False)
            lvbox.enable = False
        fig.canvas.draw_idle()

    cbox1.set_addfunc(ixy_on_off)

###################   CheckButtons  example end   ####################



###################  interactive legend example   ####################

    
    def add_leg_event(item):
        ax_line_x = legV.artists[item][0].get_xdata()
        ax_line_y = ax_line = legV.artists[item][0].get_ydata()
        x1 = min(cXX.c1.x, cXX.c2.x)
        x2 = max(cXX.c1.x, cXX.c2.x)
        s1 = ax_line_x[0]
        s2 = ax_line_x[-1]
        idx1 = 0
        idx2 = 0
        calc_values = True
        xs, xe = ax.get_xlim()
    
        if s1 > xe or s2 < xs:   # out of plot window
            calc_values = False

        """
        curr in plot window and at least one end of signal hooks to the curr window

        """
        if cXX.in_win and s1 < x2 and s2 > x1:    # out of curr window
            idx1 = np.nonzero(ax_line_x >= x1)[0][0]
            idx2 = np.nonzero(ax_line_x <= x2)[0][-1]            
        elif calc_values:
            cXX.visible = False
            idx1 = np.nonzero(ax_line_x >= xs)[0][0]
            idx2 = np.nonzero(ax_line_x <= xe)[0][-1]
        if calc_values:
            if idx1 == idx2:
                ax_line = ax_line_y[idx1]
            else:           
                ax_line = ax_line_y[idx1:idx2]

        if cbox1.pik_pik_bx:
            if calc_values:
                cYY.c1.y = max(ax_line)
                cYY.c2.y = min(ax_line)
            else:
                cYY.c1.y = 0
                cYY.c2.y = 0
            cYY.update_osc()
            cYY.visible = True
            

############################  flying labels example  #############################


    txt1 = fig.text(0.25,0.75, 'This is flying label in fig space',
                    color='red', fontsize=12, fontweight='bold')

    txt2 = ax.text(0.15,0.15, 'This is flying label in ax.transAxes space ',
                    color='darkgreen', fontsize=12, fontweight='bold',
                    transform=ax.transAxes)




##########################################################
##########################################################
######                                             #######
######       standard matplotlib plot code         #######
            

    fig.subplots_adjust(left=0.08, right=0.88, bottom=0.17) 
    fig.set_figwidth(8) # inches
    fig.set_figheight(6)
    
    np.random.seed(19680801)

    dt = 0.01
    t = np.arange(0, 5, dt)
    nse1 = np.random.randn(len(t))                 
    nse2 = np.random.randn(len(t))                 

    s1 = np.sin(2 * np.pi * 10 * t) + nse1
    s2 = np.sin(2 * np.pi * 10 * t) + nse2
    s3 = np.sin(2 * np.pi * 1 * t)
    s4 = np.sin(2 * np.pi * 5 * t)*1.5

    ax.plot(t, s1, label='s1')
    ax.plot(t, s2, label='s2')
    ax.plot(t, s3, label='s3')
    ax.plot(t, s4, label='s4')


    ax.set_xlim(0, 2)
    ax.grid(True)

    x_label = ax.set_xlabel('Time (s)')
    y_label = ax.set_ylabel('U[V]')
    ax_title = ax.set_title('Interactive Matplotlib application example')


##################################################################################
#############                                                    #################
#############        VisToole module adds only one line of code  #################
    
    """
    This almost one line adds oscilloscope-like data inspection

    There are many options in this arg --       --  optional labels to interact
                                        |       |   must be placed in fig area
                                       \|/     \|/
    """                                
    cXX, cYY, cBB, legV = Vistoole('xylegtm', tm=[txt1, txt2], fig=fig, ax=ax, 
                                   leg_addfunc=add_leg_event)

#####################                                         #####################    
#####################  just before plt.show()  instruction    #####################

    plt.show(block="idlelib" not in sys.modules)
