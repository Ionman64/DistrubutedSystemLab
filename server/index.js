var page_reload_timeout = 5; //in seconds
var page_reload_count = 0;

function update_contents(){
    page_reload_count += 1;
    $("#boardcontents_placeholder").load("/board #boardcontents_placeholder", function (data, status) {
        //alert("Data: " + data + "\nStatus: " + status);
        $("#boardcontents_status_placeholder").text(page_reload_count + ": " + status);
    });
}
function el(m) {
	return document.createElement(m);
}
function load_board_ajax() {
	$.ajax({
		url:"/board",
		method:"GET",
		dataType:"JSON",
		crossOrigin:true,
		success:function(data, status) {
			/*<div id="boardcontents_placeholder">
				<!-- The title comes here -->
				<div id="boardtitle_placeholder" class="boardtitle">%s</div>
				<input type="text" name="id" value="ID" readonly>
				<input type="text" name="entry" value="Entry" size="70%%" readonly>
				<!-- The entries come here -->
				%s
			</div>*/
			$("#board-contents").empty();
			$.each(data, function(key, value) {
				var board_entry = el("section");
				board_entry.id = "boardcontents_placeholder"; 
				var boardtitle = el("section");
				boardtitle.id = "boardtitle_placeholder";
				boardtitle.className = "boardtitle";
				board_entry.appendChild(boardtitle);
				var input = el("input");
				input.type = "text";
				input.name = "id";
				input.value = key;
				input.readonly = true;
				board_entry.appendChild(input);
				var input = el("input");
				input.type = "text";
				input.name = "entry";
				input.value = value;
				input.style.size = "70%";
				board_entry.appendChild(input);
				$("#board-contents").append(board_entry);
			});
		},
		complete:function() {
			console.log("updated board");
		}
	});
}
function add_entry_ajax() {
	$.ajax({
		url:"/board",
		method:"POST",
		dataType:"JSON",
		crossOrigin:true,
		data: {"entry":$("#entry").val()},
		sucess:function(data, status) {
			page_reload_count++;
			$("#boardcontents_status_placeholder").text(page_reload_count + ": " + status);
		},
		complete: function() {
			console.log("added new entry to contents");
		}
	});
}

function reload_countdown(remaining) {
    $("#countdown_placeholder").text("reloading page in: " + remaining + " seconds.");
    if (remaining <= 0) {
        remaining = page_reload_timeout;
        load_board_ajax();
    }
    setTimeout(function() {
        reload_countdown(remaining - 1);
    }, 1000);
}

$(document).ready(function() {
	load_board_ajax();
    reload_countdown(page_reload_timeout);
    $(".entryform").on("submit", function(e) {
    	add_entry_ajax();
    	e.preventDefault();
    	return false;
    });
});
