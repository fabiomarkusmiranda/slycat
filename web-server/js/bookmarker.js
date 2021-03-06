/*
Copyright 2013, Sandia Corporation. Under the terms of Contract
DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
rights in this software.
*/

function bookmark_manager(server_root, pid, mid) {

  var bid = null;
  if($.deparam.querystring().bid == 'clear') {
    // Remove the current model ID from localStorage to clear it
    localStorage.removeItem(mid);
    // Do nothing more to allow bookmark state to clear
  }
  else if($.deparam.querystring().bid != null) {
    bid = $.deparam.querystring().bid;
  }
  else if(localStorage.getItem(mid) != null) {
    bid = localStorage.getItem(mid);
    updateURL(bid);
  }
  var state = {}; // JSON object representing the state of the model UI
  var req = null; // ajax request

  // Updates the browser's URL with the bid (private)
  function updateURL(bid){
    var url = $.param.querystring( window.location.toString(), {"bid" : bid} );
    window.history.replaceState( null, null, url );
    // Consider using window.history.pushState instead to enable back button navigation within the model
  }

  // Updates the bookmark state (privileged)
  this.updateState = function(params){
    $.extend(state, params); // Consider using deep merge by adding true as the first parameter. However, deep merging does not work with bookmarking of expanded and collapsed dendrogram nodes since they are passed as arrays

    // Store bookmark and update the bid
    if(req)
      req.abort();

    req = $.ajax(
      {
        type : "POST",
        url : server_root + "projects/" + pid + "/bookmarks",
        contentType : "application/json",
        data: $.toJSON(state),
        processData: false,
        success: function(result)
        {
          bid = result.id;
          updateURL(bid);
          // Store latest bid in local storage
          if(mid != null)
            localStorage[mid] = bid;
          req = null;
        },
      });
  }

  // Gets the state from the current bookmark id
  this.getState = function(){
    if( $.isEmptyObject(state) && !(bid == null) ) {
      retrieveState();
    }
    return state;
  }

  // Retrieves the state for a given bookmark id (bid)
  function retrieveState(){
    $.ajax(
    {
      dataType: "json",
      url: server_root + "bookmarks/" + bid,
      async: false,
      success: function(resp){
        state = resp;
      }
    });
  }

}
