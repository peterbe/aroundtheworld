/* All of these need to be refactored for DRY some day */

var LineGraph = function(id, url, options) {

  new Rickshaw.Graph.Ajax( {
     element: document.querySelector("#" + id + " .chart"),
    renderer: 'line',
    interpolation: options.interpolation || 'linear',
    height: 300,
    width: 700,
    dataURL: url,
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
        element: document.querySelector('#' + id + ' .y-axis'),
      } );
      var x_axis = new Rickshaw.Graph.Axis.Time( { graph: graph } );
      var legend = new Rickshaw.Graph.Legend( {
         element: document.querySelector('#' + id + ' .legend'),
        graph: graph
      } );

      graph.render();

    },
  });

};


var BarGraph = function(id, url, options) {
  new Rickshaw.Graph.Ajax( {
     element: document.querySelector("#" + id + " .chart"),
    renderer: 'bar',
    height: 300,
    width: 700,
    dataURL: url,
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
        element: document.querySelector('#' + id + ' .y-axis'),
      } );

      var legend = new Rickshaw.Graph.Legend( {
         element: document.querySelector('#' + id + ' .legend'),
        graph: graph
      } );

      graph.render();

    },
  });
};


// USERS

$(function() {
  // Users
  LineGraph('chart-users', '?get=users_data', {
     interpolation: 'linear'  // or 'cardinal'
  });

  // Jobs
  LineGraph('chart-jobs', '?get=jobs_data', {
    interpolation: 'cardinal'
  });

  // Awards
  LineGraph('chart-awards', '?get=awards_data', {
     interpolation: 'cardinal'
  });

  // Miles travelled
  BarGraph('chart-miles-travelled', '?get=miles_travelled_data');
});
