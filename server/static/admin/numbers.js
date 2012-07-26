/* All of these need to be refactored for DRY some day */

// USERS

(new Rickshaw.Graph.Ajax( {
	element: document.querySelector("#chart-users .chart"),
	renderer: 'line',
  interpolation: 'linear',  // or 'cardinal'
	height: 300,
	width: 700,
  dataURL: '?get=users_data',
  onData: function(d) {
    return d.data;
  },
  onComplete: function(transport) {
    var graph = transport.graph;

    var detail = new Rickshaw.Graph.HoverDetail({
       graph: graph,
      yFormatter: function(y) {
        return y;
      }
    });

    var y_ticks = new Rickshaw.Graph.Axis.Y( {
       graph: graph,
      pixelsPerTick: 35,  // default is 75
      orientation: 'left',
      tickFormat: Rickshaw.Fixtures.Number.formatKMBT,
      element: document.querySelector('#chart-users .y-axis'),
    } );
    var x_axis = new Rickshaw.Graph.Axis.Time( { graph: graph } );
    var legend = new Rickshaw.Graph.Legend( {
       element: document.querySelector('#chart-users .legend'),
      graph: graph
    } );

    graph.render();

  },

}));


// JOBS
//
(new Rickshaw.Graph.Ajax( {
	element: document.querySelector("#chart-jobs .chart"),
	renderer: 'line',
  interpolation: 'cardinal',  // or 'linear'
	height: 300,
	width: 700,
  dataURL: '?get=jobs_data',
  onData: function(d) {
    return d.data;
  },
  onComplete: function(transport) {
    var graph = transport.graph;

    var detail = new Rickshaw.Graph.HoverDetail({
       graph: graph,
      yFormatter: function(y) {
        return y;
      }
    });

    var y_ticks = new Rickshaw.Graph.Axis.Y( {
       graph: graph,
      pixelsPerTick: 35,  // default is 75
      orientation: 'left',
      tickFormat: Rickshaw.Fixtures.Number.formatKMBT,
      element: document.querySelector('#chart-jobs .y-axis'),
    } );
    var x_axis = new Rickshaw.Graph.Axis.Time( { graph: graph } );
    var legend = new Rickshaw.Graph.Legend( {
       element: document.querySelector('#chart-jobs .legend'),
      graph: graph
    } );

    graph.render();

  },

}));


// AWARDS
//
(new Rickshaw.Graph.Ajax( {
	element: document.querySelector("#chart-awards .chart"),
	renderer: 'line',
  interpolation: 'cardinal',  // or 'linear'
	height: 300,
	width: 700,
  dataURL: '?get=awards_data',
  onData: function(d) {
    return d.data;
  },
  onComplete: function(transport) {
    var graph = transport.graph;

    var detail = new Rickshaw.Graph.HoverDetail({
       graph: graph,
      yFormatter: function(y) {
        return y;
      }
    });

    var y_ticks = new Rickshaw.Graph.Axis.Y( {
       graph: graph,
      pixelsPerTick: 35,  // default is 75
      orientation: 'left',
      tickFormat: Rickshaw.Fixtures.Number.formatKMBT,
      element: document.querySelector('#chart-awards .y-axis'),
    } );
    var x_axis = new Rickshaw.Graph.Axis.Time( { graph: graph } );
    var legend = new Rickshaw.Graph.Legend( {
       element: document.querySelector('#chart-awards .legend'),
      graph: graph
    } );

    graph.render();

  },

}));
