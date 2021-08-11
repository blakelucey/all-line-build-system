<?php

require('../main.php');
$self = '/service/index.php';
$left_col = '12em';
$input_left_col = '5em';
$ipc = new Ipc();
$stats_config = new IpcConfig($ipc, 'statistics');
$tank_monitor = new TankMonitor($ipc);
$tm_config = new IpcConfig($ipc, 'tank_monitor');



# Collect the tank information, if possible
if ($tank_monitor->can_connect()) {
   $all_tanks = $tank_monitor->get_tank_data();
   //print_var($all_tanks);
   if (count($all_tanks)) {
      $tanks = [];
      foreach ($all_tanks as $index => $tank) {
         $tanks[$index + 1] = $tank['name'] . "\t(" . number_format($tank['height'], 1) . ' inches)';
      }
   }
}
else {
   $tanks = [];
}

# Items we need on this page:
# - Dismiss alarm
# - Override low level sensor
# - Reboot system
# - Disable/enable blending
# - Command console
# - IPC console
# - Notes

# These are the predefined IPC commands.
# The format is:
#     'cmd_id' => ['human-readable name', 'json']
$predefined_commands = [
   'none' =>
      ['(None)', ''],

   'all_names' =>
      ['Show All Parameter Names', '{"request_type": "list_params"}'],
   
   'most_parameters' =>
      ['Show Most Parameter Names and Values', '{"request_type": "list_params_values"}'],
   
   'blender_settings' =>
      ['Show Blender Settings Parameter Names and Values', '{"request_type": "list_blender_settings_params"}'],

   'show' =>
      ['Show a Single Parameter', '{"request_type": "get_param", "param_name": `name here`, "index": 0}'],

   'reboot' =>
      ['Reboot Mainboard', '{"request_type": "reboot"}'],

   'reboot_arm' =>
      ['Reboot Linux', '{"request_type": "reboot_self"}'],

   'print_message' =>
      [
         'Print Message',
         '{"request_type": "pause"}' .
         '{"request_type": "set_param", "param_name": "Display Command", "param_value": 0, "index": 1}' .
         '{"request_type": "set_param", "param_name": "Display Data", "param_value": `your text here`}'
      ],

   'pause' =>
      ['Pause System', '{"request_type": "pause"}'],

   'play' =>
      ['Unpause System', '{"request_type": "play"}'],

   'save' =>
      ['Save All Changes', '{"request_type": "save_params"}']
];



function help_wrapper ($element, $help_text) {
   return [
      $element->append_attribute('class', 'has-help'),
      new HelpText($help_text)
   ];
}

function emit_predefined_commands () {
   global $predefined_commands;

   echo '<script type="text/javascript">' . PHP_EOL;
   echo 'var commands = {' . PHP_EOL;
   $index = 0;
   foreach ($predefined_commands as $key => $value) {
      $json = $value[1];
      echo '   "' . $key . '": "' . addslashes($json) . '"';
      if ($index < count($predefined_commands) - 1) echo ',';
      echo PHP_EOL;
   }
   echo '}' . PHP_EOL;
?>
$.fn.selectRange = function (start, end) {
    var e = document.getElementById($(this).attr('id'));
    if (!e) return;
    else if (e.setSelectionRange) { e.focus(); e.setSelectionRange(start, end); } /* WebKit */
    else if (e.createTextRange) { var range = e.createTextRange(); range.collapse(true); range.moveEnd('character', end); range.moveStart('character', start); range.select(); } /* IE */
    else if (e.selectionStart) { e.selectionStart = start; e.selectionEnd = end; }
};

var pick_command = function () {
   var id = $('#predefined').val();
   var area = $('#command');
   var areadom = area.get(0);
   var text = commands[id];
   var pos1 = text.indexOf('`');
   var pos2 = text.indexOf('`', pos1 + 1);
   console.log(pos1 + ' - ' + pos2);
   if (pos1 > -1 && pos2 > -1) {
      text = text.replace(/`/g, '"');
      area.val(text);
      pos1++;
      area.focus();
      area.selectRange(pos1, pos2);
   }
   else {
      area.val(text);
      area.focus();
   }
};
<?php
   echo '</script>' . PHP_EOL;
}

function var_dump_ret ($mixed = null) {
   # Old, using var_dump
   #ob_start();
   #var_dump($mixed);
   #$content = ob_get_contents();
   #ob_end_clean();
   #return $content;

   # New, using JSON directly
   $json = json_encode($mixed, JSON_PRETTY_PRINT);
   return $json;
}

function make_table ($rec) {
   $table = new Table();
   $table->append_attribute('class', 'data vertical-separators fixed-header');
   $table->add_style('font-size', '70%');
   #$table->add_style('width', '100%');

   $header = new TableHeader();
   $widths = [
      4, 6, 6, 6, 6, 8, 7, 6, 8, 6, 6.5
   ];
   foreach ($rec->columns as $index => $text) {
      $width = isset($widths[$index]) ? $widths[$index] . 'em' : '';
      $header->add_child(new TableHeaderCell($text));
   }
   $table->add_child($header);

   for ($offset = 4; $offset >= 0; $offset--) {
      # Done already?
      if (!isset($rec->rows[count($rec) - 1 - $offset])) break;

      $row = $rec->rows[count($rec) - 1 - $offset];
      $table_row = new TableRow();
      for ($col = 0; $col < count($row); $col++) {
         $table_row->add_child(new TableCell($row[$col]));
      }
      $table->add_child($table_row);
   }

   return $table;
}

class PreElement extends HtmlElement {
   protected $tag = 'pre';
   public function __construct ($text) {
      $this->text = $text;
   }
};

function separator ($text = '') {
   echo '<div class="form-header">' . $text . '</div>' . PHP_EOL;
}

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);
$page = new Page($system);
$notes_file = get_path('config') . 'notes.txt';
$notes = file_exists($notes_file) ? @file_get_contents($notes_file) : '';
$command_response = null;

$login->admin_check();

function dismiss_alarm () {
   global $system, $self;

   $system->set_param_value('Alarm Dismiss', 1);
   Page::redirect($self);
   die;
}

function set_sensor_overrides () {
   global $system, $self;

   if (!isset($_POST['override']) || !isset($_POST['submit_sensors'])) die;

   $num_sensors = $system->get_param_value('Number of Sensors');
   for ($id = 0; $id < $num_sensors; $id++) {
      $set_value = get_post('override', 0, $id);
      if ($set_value < 0 || $set_value > 2) continue;

      $system->set_param_value('Sensor Overrides', $set_value, $id);
   }

   Page::redirect($self);
   die;
}

function save_notes () {
   global $notes_file, $self;

   if (!isset($_POST['submit_notes'])) die;

   file_put_contents($notes_file, $_POST['notes']);

   Page::redirect($self . '#a_notes');
   die;
}

function execute_command () {
   global $system, $ipc, $self, $command_response;

   # Fall through if nothing was submitted.
   if (!isset($_POST['submit_command']) || !isset($_POST['command'])) return;

   $command = $_POST['command'];
   $command = preg_replace('/\r|\n|\r\n/', '', $command);
   $command_response = [];

   # Empty?
   if (empty($command) || ctype_space($command)) return;

   # Multiple commands?
   if (strpos($command, '}{')) {
      # Yes, there are multiples.
      $command = trim($command, '{}');
      $commands = explode('}{', $command);
      foreach ($commands as &$c) {
         $c = '{' . $c . '}';

         $command_response[] = $ipc->raw_request($c);
      }
   }
   else {
      $command_response[] = $ipc->raw_request($command);
   }

   # Keep it for later, eh?
   $prev_command = $_POST['command'];
}

# Responders
$action = $_GET['action'] ?? '';
switch ($action) {
case 'dismiss-alarm':
   dismiss_alarm();
   break;

case 'sensor-overrides':
   set_sensor_overrides();
   break;

case 'ipc-command':
   execute_command();
   break;

case 'notes':
   save_notes();
   break;
}

$page->header('System Service');

emit_predefined_commands();


if (isset($_POST['submit_config'])) {
   # Do settings update.

   for ($index = 0; $index < 3; $index++) {   
      if ($index == 0) {
         //$header_tag = 'Bio';
         $header_tag_short = 'bio';
         //$header_tank_tag = 'Bio tank';
      }
      if ($index == 1) {
         //$header_tag = 'Diesel';
         $header_tag_short = 'dsl';
         //$header_tank_tag = 'Diesel Tank';
      }
      if ($index == 2) {
         //$header_tag = 'Blend';
         $header_tag_short = 'blend';
         //$header_tank_tag = 'Blend';
      }
      $stats_config['min_' . $header_tag_short . '_tank_reading'] = get_post('input_stats_config', '', 'min_' . $header_tag_short . '_tank_reading');
      $stats_config['min_' . $header_tag_short . '_tank_reading_stats'] = get_post('input_stats_config', '', 'min_' . $header_tag_short . '_tank_reading_stats');
      $stats_config[$header_tag_short . '_error_ignore'] = get_post('input_stats_config', '', $header_tag_short . '_error_ignore');
      $stats_config[$header_tag_short . '_error_warn'] =   get_post('input_stats_config', '', $header_tag_short . '_error_warn');
      $stats_config['max_bad_' . $header_tag_short . '_records'] =  get_post('input_stats_config', '', 'max_bad_' . $header_tag_short . '_records');
   }
   $diesel_tank_array = [];
   foreach ($tanks as $tank_index => $tank){
      if (get_post('input_stats_config', '', 'tank_num_'. $tank_index) == True){
         array_push($diesel_tank_array, $tank_index);
      }
   }
   $stats_config['diesel_tanks'] = $diesel_tank_array;

   # Validate these against the backend.
   if (
      $stats_config->validate() &&
      count($errors) === 0
   ) {
      # No errors; we can save.
      $stats_config->save();
      
      # Refresh page.
      Page::redirect($self . '?save-success');
      #Page::redirect($self);
      die;
   }

   # Fall through to display errors.
   $had_errors = true;
}


$page->begin_section('Alarm');
$is_alarm = $system->get_param_value('Alarm State');
$form = new Form($self . '?action=dismiss-alarm');
if (!$is_alarm) {
   $form->add_child(new FormRow(
      '&nbsp;',
      new PlainText('The system is not currently in an alarm state.'),
      $left_col
   ));

   echo $form->get_html();
}
else {
   $form->add_child(new FormRow(
      'State',
      new PlainText('The system is <b>currently in an alarm state</b>.'),
      $left_col
   ));

   $form->add_child(new FormRow(
      '&nbsp;',
      new SubmitButton('submit_dismiss_alarm', false, 'Dismiss Alarm'),
      $left_col
   ));

   echo $form->get_html();

   $records = new RecordFiles($system);

   $file = $records->get_latest_file();
   if ($file !== false && count($file->rows) > 0) {
      separator('Latest Record(s)');
      $table = make_table($file);
      echo $table->get_html();
   }
}

$page->end_section();

$page->begin_section('Sensor Overrides');

$num_sensors = $system->get_param_value('Number of Sensors');
$sensor_choices = [
   0 => 'Do Not Override',
   1 => 'Force Present',
   2 => 'Force Not Present'
];
$form = new Form($self . '?action=sensor-overrides');
for ($id = 0; $id < $num_sensors; $id++) {
   $which = $system->get_param_value('Sensor Overrides', $id);

   $form->add_child(new FormRow(
      $system->get_param_value('Sensor Names', $id),
      new SelectBox('override-' . $id, "override[$id]", $sensor_choices, $which),
      $left_col
   ));
}

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('submit_sensors', false, 'Save Overrides'),
   $left_col
));
echo '<a name="e_command"></a>';

echo $form->get_html();

/*
separator('Global Parameter List');
$param_choices = array_filter($system->get_all_names(), function ($v) use ($system) {
   return !$system->get($v)->is_read_only();
});
$form = new form($self . '?action=parameter-list');
$form->add_child(new FormRow(
   'Parameter',
   new SelectBox('parameter', false, $param_choices),
   $left_col
));

$form->add_child(new FormRow(
   'Current Value',
   (new TextBox('current_value', false, '', 16, 32))
      ->append_attribute('disabled', 'disabled')
      ->append_attribute('placeholder', 'Select a Parameter'),
   $left_col
));

$form->add_child(new FormRow(
   'Force Value',
   new TextBox('force_value', false, '', 16, 32),
   $left_col
));

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('submit_parameter', false, 'Modify Parameter'),
   $left_col
));

echo $form->get_html();
*/

$page->end_section();

$page->begin_section('Execute Command');

$form = new Form($self . '?action=ipc-command#e_command');

$command_box = new SelectBox('predefined', false);
foreach ($predefined_commands as $key => $value) {
   $command_box->add_item($key, $value[0]);
}

$command_box->append_attribute('onchange', 'pick_command();');

$form->add_child(new FormRow(
   'Predefined Commands',
   $command_box,
   $left_col
));

$form->add_child(new FormRow(
   'Command',
   new TextArea('command', false, $prev_command, 4, 80),
   $left_col
));

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('submit_command', false, 'Execute Command'),
   $left_col
));

# Show the response from the previously executed command?
if ($command_response !== null) {
   function format_single_response ($form, $what) {
      global $left_col;

      $response = new PlainText('Error processing command.');

      $text = @json_decode($what, true);
      if ($text !== false) {
         $response = new PreElement(var_dump_ret($text));
      }

      $form->add_child(new FormRow(
         'Response',
         $response,
         $left_col
      ));
   }

   # Go through the response(s) and print them out.
   foreach ($command_response as $what) {
      format_single_response($form, $what);
   }
}

echo $form->get_html();

$page->end_section();

$page->begin_section('System Notes');
echo '<a name="a_notes"></a>';
$form = new Form($self . '?action=notes');
$form->add_child(new FormRow(
   'Notes',
   new TextArea('notes', false, $notes, 6, 60),
   $left_col
));

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('submit_notes', false, 'Save Notes'),
   $left_col
));

echo $form->get_html();

$page->end_section();




$page->begin_section('Admin Configs');
$form = new Form($self . '?action=config');
$form->add_child($bio_config_div = new DivElement());
$form->add_child($dsl_config_div = new DivElement());
$form->add_child($blend_config_div = new DivElement());

foreach ($form->get_children() as $index => $child) {   
   if ($index == 0) {
      $header_tag = 'Bio';
      $header_tag_short = 'bio';
      $header_tank_tag = 'Bio Tank';
   }
   if ($index == 1) {
      $header_tag = 'Diesel';
      $header_tag_short = 'dsl';
      $header_tank_tag = 'Diesel Tank';
   }
   if ($index == 2) {
      $header_tag = 'Blend';
      $header_tag_short = 'blend';
      $header_tank_tag = 'Bio Tank';
   }
   
   $child->add_style('width', '33.3%');
   $child->add_style('float', 'left');
   $child->add_style('position', 'relative');
   $child->add_child(new FormHeader($header_tag.' error checking'));

   $child->add_child(new FormRow(
      'Minimum '. $header_tank_tag .' Level for stats',
      help_wrapper(
         new TextBox('stats_min_' . $header_tag_short . '_tank_reading_stats', 'input_stats_config[min_' . $header_tag_short . '_tank_reading_stats]', $stats_config['min_' . $header_tag_short . '_tank_reading_stats'], 5, 20),
         'The threshold the system has for determine if the record should show up on the statistics page.'
      ),
      $left_col,
      $stats_config->invalid['min_' . $header_tag_short . '_tank_reading_stats']
   ));
   $child->add_child(new FormRow(
      $header_tag . ' Error for stats',
      help_wrapper(
         new TextBox('stats_' . $header_tag_short . '_error_ignore', 'input_stats_config[' . $header_tag_short . '_error_ignore]', $stats_config[$header_tag_short . '_error_ignore'], 5, 20),
         'Error that determines when the meter-tank error is large enough to include it in the statistics page (histograms).'
      ),
      $left_col,
      $stats_config->invalid[$header_tag_short . '_error_ignore']
   ));
   $child->add_child(new FormRow(
      'Minimum '. $header_tank_tag .' Level for alert',
      help_wrapper(
         new TextBox('stats_min_' . $header_tag_short . '_tank_reading', 'input_stats_config[min_' . $header_tag_short . '_tank_reading]', $stats_config['min_' . $header_tag_short . '_tank_reading'], 5, 20),
         'The threshold the system has for alerting a significant difference between tank and meter.'
      ),
      $left_col,
      $stats_config->invalid['min_' . $header_tag_short . '_tank_reading']
   ));
   $child->add_child(new FormRow(
      $header_tag . ' Error for alert',
      help_wrapper(
         new TextBox('stats_' . $header_tag_short . '_error_warn', 'input_stats_config[' . $header_tag_short . '_error_warn]', $stats_config[$header_tag_short . '_error_warn'], 5, 20),
         'Error that determines when the meter-tank error is large enough to send out an email alert.'
      ),
      $left_col,
      $stats_config->invalid[$header_tag_short . '_error_warn']
   ));
   $child->add_child(new FormRow(
      'Maximum # of Bad ' . $header_tag .  ' Records',
      help_wrapper(
         new TextBox('stats_max_bad_' . $header_tag_short . '_records', 'input_stats_config[max_bad_' . $header_tag_short . '_records]', $stats_config['max_bad_' . $header_tag_short . '_records'], 5, 4),
         'The number of bad records in a row the system needs to see in order to send the alert email address.'
      ),
      $left_col,
      $stats_config->invalid['max_bad_' . $header_tag_short . '_records']
   ));
}

$form->add_child(new FormHeader('Diesel Tanks'));
if (count($tanks)) {
   foreach ($tanks as $tank_index => $tank){
      $checked = in_array($tank_index,$stats_config['diesel_tanks']);
      $form->add_child(
         $checkbox = new CheckBox('tank_num_'. $tank_index, 'input_stats_config[tank_num_'. $tank_index . ']', $tank, $checked)
      );
      $checkbox->add_style('margin-left','5%');
      //print_var($tank . ' index ' . $tank_index);
   }
}
else {
   $form->add_child(new FormRow(
      'Tank to Monitor',
      new PlainText('Not yet connected to tank monitor.'),
      $left_col
   ));
}

$form->add_child(new WhiteSpace('100%'));

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('submit_config', false, 'Save Configurations'),
   '5%'
));

//print_var('Diesel takns to monitor:');
//print_var($stats_config['diesel_tanks']);

echo $form->get_html();

$page->end_section();



$page->begin_section('System Statistics');

# Lots of raw HTML here. It's a service page, after all.
echo '<div class="form-header">Uptime</div>';
echo '<pre>' . `uptime` . '</pre>';

echo '<div class="form-header">Memory Overview</div>';
echo '<pre>' . `free` . '</pre>';

echo '<div class="form-header">Console Users</div>';
echo '<pre>' . `who -H` . '</pre>';

echo '<div class="form-header">Free Disk Space</div>';
echo '<pre>' . `df -h` . '</pre>';

$page->end_section();

$page->footer();

?>
