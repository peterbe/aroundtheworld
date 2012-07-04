$(document).ready(function() {
  function draw(categories, data) {

    var chart = new Highcharts.Chart({
       chart: {
          renderTo: 'question-alternatives',
           type: 'bar'
       },
      title: {
         text: 'Distribution of alternatives'
      },
      xAxis: {
         categories: categories,
          title: {
             text: null
          }
      },
      yAxis: {
         min: 0,
          title: {
             text: 'Percentage',
              align: 'high'
          },
        labels: {
           overflow: 'justify'
        }
      },
      tooltip: {
         formatter: function() {
           return this.y + '%';
         }
      },
      plotOptions: {
         bar: {
            dataLabels: {
               enabled: false
            }
         }
      },
      legend: {
         enabled: false
      },
      credits: {
         enabled: false
      },
			series: [{
         name: 'Percentage of people choosing this',
        data: data
      }]
    });
  }
  $.getJSON(location.href + 'alternatives.json', function(response) {
    draw(response.categories, response.data);
  });
});
