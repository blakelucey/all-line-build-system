if (!!window.EventSource) {
   var es = new EventSource('/update/?info');
   es.addEventListener('message', function (e) {
      var data = $.parseJSON(e.data);
      var task = data['process'] == 'write' ? 'Writing firmware: ' : 'Verifying firmware: ';
      var pct = data['percent'];
      $('.progress-bar .background').css('width', pct + '%');
      $('#task-text').html(task + pct.toFixed(1) + '%');
      if (data['process'] == 'read' && pct > 99.9) {
         window.location.href = '/';
      }
   });
}
