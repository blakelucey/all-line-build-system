<?php

require('../main.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);
$reporting = new IpcConfig($ipc, 'reporting');
$alert = new IpcConfig($ipc, 'alert');
$tank_monitor = new TankMonitor($ipc);
$tm_config = new IpcConfig($ipc, 'tank_monitor');
$ntp_config = new NtpConfig($ipc);
$had_errors = false;
$errors = [];
$left_col = '12em';
$blend_left_col = '0';

$login->admin_check();

# Collect the tank information, if possible
if ($tank_monitor->can_connect()) {
   $all_tanks = $tank_monitor->get_tank_data();
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

function help_wrapper ($element, $help_text) {
   return [
      $element->append_attribute('class', 'has-help'),
      new HelpText($help_text)
   ];
}

function trim_array ($array) {
   $trimmed = array_map(trim, $array);
   $filtered = array_filter($trimmed, function ($value) {
      return strlen($value);
   });
   $unique = array_unique($filtered);
   return $unique;
}

if (isset($_POST['blend_submit'])) {
   # Do blending settings update.
   $main_blend = get_post('main_blend');
   $additive_blend = get_post('additive_blend');
   $blend_percentage = get_post('blend_percentage');

   $main_blend_param = $system->get('Main Product');
   $additive_blend_param = $system->get('Additive Product');
   $blend_percentage_param = $system->get('Blend Percentage');

   if (
      !$main_blend_param->validate_value($main_blend) ||
      !$additive_blend_param->validate_value($additive_blend) ||
      !$blend_percentage_param->validate_value($blend_percentage)
   ) {
      # Something did not work.
      $errors['blend_errors'] = 'Values must be 0.0 to 100.0, inclusive.';
   }

   if (count($errors) === 0) {
      # Looks OK!
      $main_blend_param->set($main_blend);
      $additive_blend_param->set($additive_blend);
      $blend_percentage_param->set($blend_percentage);

      $system->save_params();
      Page::redirect('/reporting/index.php?save-success');
      die;
   }

   # Fall through to display errors.
}
else {
   # Load in the blending settings.
   $main_blend = $system->get_formatted_param_value('Main Product');
   $additive_blend = $system->get_formatted_param_value('Additive Product');
   $prefix = $system->get_param_value('Product Prefix');
   $blend_percentage = $system->get_formatted_param_value('Blend Percentage');
}

if (isset($_POST['dt_submit'])) {
   # Do date, time or timezone update.
   $ntp_enabled = isset($_POST['ntp_config']['enabled']);
   $ntp_timezone = $_POST['ntp_config']['timezone'];
   $ntp_date = $_POST['ntp_config']['date'] ?? false;
   $ntp_time = $_POST['ntp_config']['time'] ?? false;

   if (!$ntp_enabled) {
      if (!DateBox::validate($ntp_date) || !TimeBox::validate($ntp_time)) {
         $errors['ntp_config_date_time'] = 'Invalid date/time.';
      }
   }

   if ($ntp_date !== false) $ntp_date = DateBox::to_datetime($ntp_date);
   if ($ntp_time !== false) $ntp_time = TimeBox::to_datetime($ntp_time);

   if (count($errors) === 0) {
      # Looks OK!
      $ipc->request([
         'request_type' => 'set_ntp',
         'enabled' => $ntp_enabled
      ]);

      $ipc->request([
         'request_type' => 'set_timezone',
         'timezone' => $ntp_timezone
      ]);

      if (!$ntp_enabled) {
         $iso = $ntp_date->format('Y-m-d') . 'T' . $ntp_time->format('H:i:s');
         $iso .= '+00:00';

         $ipc->request([
            'request_type' => 'set_date_and_time',
            'iso' => $iso,
            'set_local' => true
         ]);
      }

      # Refresh page.
      Page::redirect('/reporting/index.php?save-success');
      die;
   }

   # Fall through.
}
else {
   # Load in the date and time settings.
   $ntp_enabled = $ntp_config->enabled;
   $ntp_timezone = $ntp_config->timezone;
}

if (isset($_POST['submit'])) {
   # Do settings update.
   #print_var($_POST);

   $site_name = get_post('site_name');
   $password = get_post('password');
   $set_password = strlen($password) > 0;

   if (strlen($site_name) > 31) {
      $site_name = substr($site_name, 0, 31);
   }

   if ($set_password) {
      if (preg_match('/^[0-9]{1,7}$/', $password) !== 1) {
         $errors['password'] = 'Invalid password; numeric only, up to 7 digits.';
      }
   }

   $alert['enabled'] = isset($_POST['alert']['enabled']);
   $alert['recipients'] = trim_array(explode("\n", $_POST['alert']['recipients'] ?? ''));
   $alert['text'] = get_post('alert', '', 'text');

   $reporting['enabled'] = isset($_POST['reporting']['enabled']);
   $reporting['limit'] = isset($_POST['reporting']['limit']);
   $reporting['recipients'] = trim_array(explode("\n", $_POST['reporting']['recipients'] ?? ''));
   $reporting['text'] = $_POST['reporting']['text'] ?? '';
   $reporting['when'] = $_POST['reporting']['when'] ?? '';

   # Tank monitor validation
   $tm_config['host'] = get_post('tm_config', '', 'host');
   $tm_config['enabled'] = isset($_POST['tm_config']['enabled']);
   $tm_config['port'] = get_post('tm_config', '', 'port');
   $tm_config['tank_id'] = get_post('tm_config', '', 'tank_id');
   $tm_config['low_level'] = get_post('tm_config', '', 'low_level');
   $tm_config['save_history'] = isset($_POST['tm_config']['save_history']);

   # Validate these against the backend.
   if (
      $reporting->validate() &&
      $alert->validate() &&
      $tm_config->validate() &&
      count($errors) === 0
   ) {
      # No errors; we can save.
      $reporting->save();
      $alert->save();
      $tm_config->save();

      if ($set_password) {
         $system->set_param_value('Password', $password);
      }

      $system->set_param_value('Site Name', $site_name);
      $system->save_params();

      # Refresh page.
      Page::redirect('/reporting/index.php?save-success');
      die;
   }

   # Fall through to display errors.
   $alert['recipients'] = implode("\n", $alert['recipients']);
   $reporting['recipients'] = implode("\n", $reporting['recipients']);
   $had_errors = true;
} else {
   # Fill in values.
   $site_name = $system->get_param_value('Site Name');
   if ($system->get_param_value('Password') == 0) {
      $password_placeholder = '(Not Set)';
   }
   else {
      $password_placeholder = '(Set)';
   }

   $alert['recipients'] = implode("\n", $alert['recipients']);
   $reporting['recipients'] = implode("\n", $reporting['recipients']);
}

$page = new Page($system);
$page->header('Configuration');
if ($had_errors) $page->error_banner();

# Set up the blend form
$blend_form = new Form('/reporting/index.php');

$blend_form->add_child(new FormRow(
   '&nbsp;',
   [
      new PlainText('The blender will monitor the flow of ' . $prefix . ' '),
      new TextBox('main_blend', false, $main_blend, 3, 5),
      new PlainText(' and add ' . $prefix . ' '),
      new TextBox('additive_blend', false, $additive_blend, 3, 5),
      new PlainText(' to make ' . $prefix . ' '),
      new TextBox('blend_percentage', false, $blend_percentage, 3, 5),
      new PlainText('.')
   ],
   $blend_left_col,
   $errors['blend_errors']
));

$blend_form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('blend_submit', false, 'Save Blending Settings'),
   $blend_left_col
));

# And then the date and time form
$dt_form = new Form('/reporting/index.php');
$timezones = DateTimeZone::listIdentifiers(); # Only US: DateTimeZone::PER_COUNTRY, 'US');
$timezones = array_combine($timezones, $timezones);

$dt_form->add_child(new FormRow(
   '&nbsp;',
   (new CheckBox('ntp_enabled', 'ntp_config[enabled]', 'Use the Internet to set the date and time', $ntp_enabled))->
      set_attribute('onchange', 'layout();'),
   $left_col
));

$dt_form->add_child((new FormRow(
   'Time Zone',
   new SelectBox('ntp_timezone', 'ntp_config[timezone]', $timezones, $ntp_timezone),
   $left_col
))->set_attribute('id', 'tzdiv'));

$dt_form->add_child((new FormRow(
   'Date and Time',
   [
      new DateBox('ntp_date', 'ntp_config[date]'),
      new PlainText('&nbsp; at '),
      new TimeBox('ntp_time', 'ntp_config[time]')
   ],
   $left_col,
   $ntp_config_date_time
))->set_attribute('id', 'dtdiv'));

$dt_form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('dt_submit', false, 'Save Date and Time'),
   $left_col
));

$dt_script = <<<"EOL"
<script type="text/javascript">
function layout () {
   sel = $('#ntp_enabled:checked');
   tz = $('#tzdiv');
   dt = $('#dtdiv');
   sel.length ? (tz.show(), dt.hide()) : (tz.hide(), dt.show());
}

$(layout);
</script>
EOL;

# And now the general options and reporting form
$form = new Form('/reporting/index.php');

$form->add_child(new FormHeader('Site Name and Password'));

$form->add_child(new FormRow(
   'Site Name',
   [
      (new TextBox('site_name', false, $site_name, 16, 30))->append_attribute('class', 'has-help'),
      new HelpText('A name for this site. Up to 30 characters.')
   ],
   $left_col,
   $errors['site_name']
));

$form->add_child(new FormRow(
   'Keypad Password',
   [
      (new TextBox('password', false, $password, 10, 7))
         ->append_attribute('class', 'has-help')
         ->append_attribute('placeholder', $password_placeholder),
      new HelpText('Used at the keypad only; enter 0 to disable.')
   ],
   $left_col,
   $errors['password']
));

$form->add_child(new FormHeader('Tank Monitor Configuration'));

$form->add_child(new FormRow(
   '&nbsp;',
   new CheckBox('tm_enabled', 'tm_config[enabled]', 'Enable querying a local TLS-350-compatible tank monitor', $tm_config['enabled'] == 1, 1),
   $left_col
));

$form->add_child(new FormRow(
   '&nbsp;',
   new CheckBox('tm_save_history', 'tm_config[save_history]', 'Save tank monitor readings for all tanks when saving a blending record', $tm_config['save_history']),
   $left_col
));

$form->add_child(new FormRow(
   'IP Address',
   help_wrapper(
      new TextBox('tm_host', 'tm_config[host]', $tm_config['host'], 15, 48),
      'The IP address or host name of the tank monitor.'
   ),
   $left_col,
   $tm_config->invalid['host']
));

$form->add_child(new FormRow(
   'Port',
   help_wrapper(
      new TextBox('tm_port', 'tm_config[port]', $tm_config['port'], 4, 5),
      'The TCP port to use.'
   ),
   $left_col,
   $tm_config->invalid['port']
));

if (count($tanks)) {
   $form->add_child(new FormRow(
      'Tank to Monitor',
      new SelectBox('tm_tank_id', 'tm_config[tank_id]', $tanks, $tm_config['tank_id']),
      $left_col
   ));
}
else {
   $form->add_child(new FormRow(
      'Tank to Monitor',
      new PlainText('Not yet connected to tank monitor.'),
      $left_col
   ));
}

$form->add_child(new FormRow(
   'Low Level',
   help_wrapper(
      new TextBox('tm_low_level', 'tm_config[low_level]', $tm_config['low_level'], 4, 5),
      'The low level set point, in inches.'
   ),
   $left_col,
   $tm_config->invalid['low_level']
));


/*
$form->add_child(new FormHeader('Outgoing Email Setup'));

$form->add_child(new FormRow(
   'SMTP Server',
   [
      (new TextBox('server', false, $server, 20, 150))->has_help(),
      new HelpText('This is the IP address or hostname of the outgoing mail server.')
   ],
   $left_col,
   $errors['server']
));

$form->add_child(new FormRow(
   'Server Port',
   [
      (new TextBox('port', false, $port, 3, 5))->has_help(),
      new HelpText('This is the TCP port you want to connect to the server on.')
   ],
   $left_col,
   $errors['port']
));

$form->add_child(new FormRow(
   'Login/Username',
   [
      (new TextBox('username', false, $username, 16, 150))->has_help(),
      new HelpText('The email account\'s username.')
   ],
   $left_col,
   $errors['username']
));

$form->add_child(new FormRow(
   'Password',
   [
      (new PasswordBox('password', false, 16, 150))->has_help(),
      new HelpText('The account\'s password. Enter this <b>only</b> when you wish to change it.')
   ],
   $left_col,
   $errors['password']
));

$form->add_child(new FormRow(
   '&nbsp;',
   new CheckBox('alsmtp', false, 'Use the All-Line Equipment email notification service. Above settings will not be used.', $alsmtp == true, '1'),
   $left_col
));
*/

$form->add_child(new FormHeader('Alerts'));

$form->add_child(new FormRow(
   '&nbsp;',
   new CheckBox('alert_enabled', 'alert[enabled]', 'Enable sending alert messages', $alert['enabled'] == true, '1'),
   $left_col
));

$form->add_child(new FormRow(
   'Send Alert Emails to',
   [
      new TextArea('alert_recipients', 'alert[recipients]', $alert['recipients'], 6, 50),
      new BreakElement(),
      new PlainText('Enter one email address per line, up to 6 total.')
   ],
   $left_col,
   $alert->invalid['recipients']
));

$form->add_child(new FormRow(
   'Additional Text',
   [
      new TextArea('alert_text', 'alert[text]', $alert['text'], 4, 40),
      new BreakElement(),
      new PlainText('This text will be sent along with the alert text.')
   ],
   $left_col,
   $alert->invalid['text']
));

$form->add_child(new FormHeader('Reports'));

$form->add_child(new FormRow(
   '&nbsp;',
   new CheckBox('report_enabled', 'reporting[enabled]', 'Enable sending daily reports', $reporting['enabled'] == true, '1'),
   $left_col
));

$form->add_child(new FormRow(
   '&nbsp;',
   new CheckBox('report_limit', 'reporting[limit]', 'Limit reports to only entries created on that day', $reporting['limit'] == true, '1'),
   $left_col
));

$form->add_child(new FormRow(
   'Send Report Emails to',
   [
      new TextArea('report', 'reporting[recipients]', $reporting['recipients'], 6, 50),
      new BreakElement(),
      new PlainText('Enter one email address per line, up to 6 total.')
   ],
   $left_col,
   $reporting->invalid['recipients']
));

$form->add_child(new FormRow(
   'Additional Text',
   [
      new TextArea('report_text', 'reporting[text]', $reporting['text'], 4, 40),
      new BreakElement(),
      new PlainText('This text will be sent along with the report text.')
   ],
   $left_col,
   $reporting->invalid['text']
));

$form->add_child(new FormRow(
   'Report Send Time',
   [
      (new TimeBox('when', 'reporting[when]', $reporting['when']))->has_help(),
      new HelpText('Reports are sent at this time. Use 24-hour times only.')
   ],
   $left_col,
   $reporting->invalid['when']
));

$form->add_child(new FormHeader(''));

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('submit', false, 'Save Options'),
   $left_col
));

# Actual page building.
echo $dt_script;

$page->begin_section('Blending Settings');
echo $blend_form->get_html();
$page->end_section();

$page->begin_section('Date and Time');
echo $dt_form->get_html();
$page->end_section();

$page->begin_section('Options');
echo $form->get_html();
$page->end_section();

$page->footer();

?>
