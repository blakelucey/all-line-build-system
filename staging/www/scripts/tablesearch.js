// Auto-searches a table's content for 'text', hides non-matching rows and
// highlights matching cells.
jQuery.fn.extend({
   tablesearcher: function (textid) {
      tableSearch(textid, this);
   }
});

var tableSearch = function (textid, table) {
   var element = $('#' + textid);

   if (element.length == 0) return;

   element.on('keyup', function (e) {
      tableSearchImpl(table, $(e.target).val());
   });

   element.on('keydown', function (e) {
      if (e.keyCode == 13) {
         e.preventDefault();
         return false;
      }
   });
};

var tableSearchImpl = function (table, text) {
   rows = table.children('tbody').children('tr');
   if (rows.length == 0) return;

   text = text.toLowerCase();

   rows.each(function () {
      row = $(this);
      cells = row.children();

      // Does the input require us to show everything?
      if (text == "") {
         cells.each(function () {
            $(this).removeClass("highlight");
         });
         row.show();
         return;
      }

      // Search the searchable cells:
      foundinrow = false;
      cells.each(function () {
         cell = $(this);
         if (!cell.hasClass("nonsearchable")) {
            if (cell.text().toLowerCase().indexOf(text) > -1) {
               cell.addClass("highlight");
               foundinrow = true;
            } else {
               cell.removeClass("highlight");
            }
         }
      });

      // If we found it at all, the whole row stays:
      if (!foundinrow) row.hide();
      else row.show();
   });
};
