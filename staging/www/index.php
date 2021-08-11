<?php

require('main.php');

$ipc = new Ipc();
$web_users = new WebUserConfig();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);
$tank_monitor = new TankMonitor($ipc);

$page = new Page($system);
$page->header();

$remote_enable = $system->get_param_value('Remote Enable');
$switch_offset = 52;
$switch_position = $remote_enable ? -$switch_offset : 0;

# Older versions of IE cannot handle this page at all, unfortunately.
if (is_old_ie()) {
   $page->begin_section($system->get_param_value('Product Name'));
   ?><p>
      You are using an old version of Microsoft Internet Explorer. This page uses
      real-time monitoring software that is not compatible with these browsers.
   </p>
   <p>
      Supported browsers include:
   </p>
   <ul>
      <li>Mozilla Firefox</li>
      <li>Google Chrome</li>
      <li>Apple Safari</li>
      <li>Microsoft Edge (slow status updates)</li>
      <li>Microsoft Internet Explorer, versions 9 and up (also slow status updates)</li>
   </ul><?php
   $page->end_section();
   $page->footer();
   die;
}
else if (is_edge()) {
   $page->begin_section($system->get_param_value('Product Name') . ' Status');
   ?><p class="center">
      You are using Microsoft Edge. The display below updates once every 10 seconds
      on this browser because it is not compatible with real-time status updates.
   </p><?php
}
else {
   $page->begin_section($system->get_param_value('Product Name') . ' Status');
}

?><div id="display"></div><?php

# Only administrators can use the keypad.
if ($login->get_user()->has_permission('admin')):
?>
<table class="keypad">
   <tr>
<?php
   $indicators = $ipc->request([
      'request_type' => 'get_indicator_info'
   ]);

   echo '<td rowspan="2" valign="top" style="width: 6em">';
   echo '<div id="indicators">';

   foreach ($indicators['indicators'] as $idx => $i) {
      echo '<div class="indicator"><div class="led ' . $i['color'] . ' off" id="led-' . $idx . '"></div>' . $i['text'] . '</div>';
   }

   echo '</div>';
   echo '</td>';
?>
      <td><a class="keypad-key" href="#" onclick="keypress('1');">1</a></td>
      <td><a class="keypad-key" href="#" onclick="keypress('2');">2</a></td>
      <td><a class="keypad-key" href="#" onclick="keypress('3');">3</a></td>
   </tr>
   <tr>
      <td><a class="keypad-key" href="#" onclick="keypress('4');">4</a></td>
      <td><a class="keypad-key" href="#" onclick="keypress('5');">5</a></td>
      <td><a class="keypad-key" href="#" onclick="keypress('6');">6</a></td>
   </tr>
   <tr>
      <td rowspan="2">
         <div class="toggle-switch">
         <div>ALLOW RUN</div>
         <a href="#" onclick="toggle(this);"></a>
         <div>STOP</div>
         </div>
      </td>
      <td><a class="keypad-key" href="#" onclick="keypress('7');">7</a></td>
      <td><a class="keypad-key" href="#" onclick="keypress('8');">8</a></td>
      <td><a class="keypad-key" href="#" onclick="keypress('9');">9</a></td>
   </tr>
   <tr>
      <td><a class="keypad-key" href="#" onclick="keypress('N');">NO</a></td>
      <td><a class="keypad-key" href="#" onclick="keypress('0');">0</a></td>
      <td><a class="keypad-key" href="#" onclick="keypress('Y');">YES</a></td>
   </tr>
</table>
<?php endif; # Keypad ?>

<style type="text/css">
   .display-screen {
      text-align: center;
   }

   .display-chars {
      background-color: #222;
      padding: 3px;
      display: inline-block;
      *display: inline; /* IE again */
      overflow: auto;
   }

   .display-char {
      float: left;
      width: 16px;
      height: 25px;
      margin: 0 1px 1px 0;
      background-image: url(/images/chars.png);
      background-repeat: no-repeat;
      background-position: 0 0;
   }

   .display-end-row {
      float: left;
      clear: both;
   }

   .keypad {
      margin: auto;
      border: 1px solid #aaa;
      border-radius: 12px;
      padding: 1em;
      margin-top: 1em;
   }

   .keypad tr td {
      border: none;
      width: 54px;
      height: 54px;
      padding: 4px;
      margin: 0;
   }

   .keypad-key {
      margin: 0;
      padding: 1px;
      display: block;
      width: 54px;
      height: 54px;
      border: 1px solid #aaa;
      border-radius: 6px;
      text-align: center;
      text-decoration: none;
      font-size: 16pt;
      color: black;
      line-height: 54px;
   }

   .keypad-key:hover {
      background: #eee;
      border-width: 2px;
      padding: 0;
   }

   .toggle-switch {
      text-align: center;
   }

   .toggle-switch div {
      font-size: 9pt;
      text-align: center;
      margin: 0 0 0.4em 0;
   }

   .toggle-switch a {
      display: inline-block;
      *display: inline;
      width: 37px;
      height: 79px;
      background: url(/images/switch.png) no-repeat;
      background-position: <?= $switch_position . 'px' ?>;
   }

   div.indicator {
      padding: 0.5em 0 0.5em 0;
      font-size: 9pt;
      line-height: 2.2em;
      border: 1px solid #aaa;
      border-radius: 6px;
      margin-bottom: 0.5em;
      text-transform: uppercase;
   }

   div.indicator div.led {
      float: left;
      width: 10px;
      height: 10px;
      border-radius: 8px;
      border: 1px solid #aaa;
      margin: 0.5em;
   }

   div.indicator div.led.green {
      background: #4f4;
   }

   div.indicator div.led.red {
      background: #f44;
   }

   div.indicator div.led.off {
      background: none;
   }
</style>

<script type="text/javascript">
var numLeds = <?= count($indicators['indicators']) ?>;

function Display (div_id) {
   this.div_id = div_id;

   this.rows = 6;
   this.cols = 24;
   this.max_row = 5;
   this.max_col = 23;

   this.row = 0;
   this.col = 0;

   this.cursor_row = 0;
   this.cursor_col = 0;
   this.cursor_enabled = false;
   this.cursor_timer = null;
   this.cursor_visible = false;
   this.cursor_period = 320;
   this.cursor_char = 0x94;

   this.chars = new Array(this.rows * this.cols);

   this.char_width = 16;
   this.char_height = 25;

   this.char_div_width = 17;
   this.char_div_height = 26;

   this.cursor_set_enabled = function (state) {
      state = !!state;
      if (state) this.cursor_on();
      else this.cursor_off();
   };

   this.cursor_on = function () {
      if (this.cursor_enabled) return;
      this.cursor_timer = window.setInterval(
         (function (self) { return function () { self.cursor_blink(); }})(this),
         this.cursor_period
      );
      this.cursor_enabled = true;
      this.cursor_visible = true;
   };

   this.cursor_off = function () {
      if (!this.cursor_enabled) return;
      if (this.cursor_timer) {
         window.clearInterval(this.cursor_timer);
      }
      this.cursor_enabled = false;
      this.cursor_visible = false;
   };

   this.cursor_blink = function () {
      this.cursor_visible = !this.cursor_visible;
      this.refresh();
   };

   this.set_char = function (row, col, ch) {
      row = row % this.rows;
      col = col % this.cols;

<?php /* Handle special characters */ ?>
      //ch = (ch < 0x20 ? ch - 0x18 + 0x87 : ch);

      this.chars[(row * this.cols) + col] = ch;
   };

   this.get_char = function (row, col) {
      row = row % this.rows;
      col = col % this.cols;

      return this.chars[(row * this.cols) + col];
   };

   this.refresh = function () {
      var ch;

      for (var r = 0; r < this.rows; r++) {
         for (var c = 0; c < this.cols; c++) {
            if (this.cursor_visible && this.cursor_row == r && this.cursor_col == c) {
               ch = this.cursor_char;
            }
            else {
               ch = this.get_char(r, c);
            }

            $('#' + div_id + ' #display-char-' + r + '-' + c).css(
               'background-position', '-' + ((ch - 32) * this.char_width) + 'px 0'
            );
         }
      }
   };

   this.clear = function () {
      for (var c = 0; c < this.rows * this.cols; c++) {
         this.chars[c] = 32;
      }
      this.row = 0;
      this.col = 0;
   };

   this.move = function (r, c) {
      this.row = r % this.rows;
      this.col = c % this.cols;
   };

   this.print = function (text) {
      for (var i = 0; i < text.length; i++) {
         this.set_char(this.row, this.col, text.charCodeAt(i));
         this.col++;
      }
   };

   var div = $('#' + div_id);
   if (div.length == 0) return;

   div.addClass('display-screen');

   var subdiv = $('<div class="display-chars"></div>');

   for (var r = 0; r < this.rows; r++) {
      for (var c = 0; c < this.cols; c++) {
         char_div = $('<div class="display-char" id="display-char-' + r + '-' + c + '"></div>');
         subdiv.append(char_div);
      }
      br_div = $('<div class="display-end-row"></div>');
      subdiv.append(br_div);
   }

   div.append(subdiv);
};

function RealTimeStatus () {
   this.frequency = 10000;
   this.callback = null;
   this.req = 0;

   this.parse = function (data) {
      return $.parseJSON(data);
   };

   this.fetch = function () {
      var me = this;
      me.req++;

      if (typeof this.esource === 'undefined') {
         $.ajax({
            'url': '/compat_display.php?r=' + me.req
         }).done(function (data) {
            if (me.callback != null) {
               me.callback(me.parse(data));
               window.setTimeout(me.fetch.bind(me), me.frequency);
            }
         });
      }
   };

   if (!!window.EventSource) {
      var me = this;
      this.esource = new EventSource('/display.php');
      this.esource.addEventListener('message', function (e) {
         me.callback(me.parse(e.data));
      }, false);
   }

   this.fetch();
};

function keypress (k) {
   $.ajax({'url': '/display.php?q=<?= $system->get_param_value('Password') ?>&k=' + k});
};

function toggle (t) {
   $.ajax({'url': '/display.php?q=<?= $system->get_param_value('Password') ?>&t'});
   var pos = parseInt($(t).css('background-position'));
   $(t).css('background-position', (pos < 0 ? 0 : -<?= $switch_offset ?>) + 'px');
};

disp = new Display('display');

stat = new RealTimeStatus();
stat.callback = function (info) {
   disp.clear();

   if (typeof info === 'undefined') {
      disp.move(0, 0);
      disp.print('Unable to get display.');
   }
   else {
      for (var i = 0; i < info['rows']; i++) {
         disp.move(i, 0);
         disp.print(info['data'][i]);
      }

      states = info['indicator_states'];
      for (var i = 0; i < numLeds; i++) {
         led = $('#led-' + i);
         if (states & (1 << i)) {
            led.removeClass('off');
         }
         else {
            led.addClass('off');
         }
      }

      disp.cursor_row = info['cursor_row'];
      disp.cursor_col = info['cursor_column'];
      disp.cursor_set_enabled(info['cursor_enabled']);
   }

   disp.refresh();
};

$(function () {
   $(document).keypress(function (e) {
      if ('0123456789ynYN'.indexOf(String.fromCharCode(e.which)) >= 0) {
         keypress(String.fromCharCode(e.which).toUpperCase());
      }
   });
});

</script>
<?php

if ($tank_monitor->can_connect()) {
   $height = $tank_monitor->get_recent_reading();
   if ($height !== false) {
      $height = number_format($height, 1);
      ?>
         <div style="margin-top: 1em;" class="center">
         Tank reading as of <?= date('h:i A') ?> is <?= $height ?> inches.
         </div>
      <?php
   }
}

$page->end_section();

$page->footer();

?>
