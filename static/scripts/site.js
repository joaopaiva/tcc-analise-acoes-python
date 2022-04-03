var Site = function(){
	this.symbol = "PETR4.SA";
};

Site.prototype.Init = function(){
	this.GetQuote();
	$("#symbol").on("click", function(){
		$(this).val("");
	});
};

Site.prototype.simpleMovingAverage = function (data, window = 5, last = false) {

	// console.log(Object.keys(prices));

	var date = Object.keys(data);
	var prices = Object.values(data);

	if (!prices || prices.length < window) {
	  return [];
	}
  
	let index = window - 1;
	const length = prices.length + 1;
  
	const simpleMovingAverages = [];
  
	while (++index < length) {
	  const windowSlice = prices.slice(index - window, index);
	  const sum = windowSlice.reduce((prev, curr) => prev + curr, 0);
	  simpleMovingAverages.push(sum / window);
	}

	if(last == true)
		return simpleMovingAverages.slice(-1);

	return simpleMovingAverages;
}

Site.prototype.GetQuote = function(){
	// store the site context.
	var that = this;

	// pull the HTTP REquest
	$.ajax({
		url: "/quote?symbol=" + that.symbol,
		method: "GET",
		cache: false
	}).done(function(data) {

		// set up a data context for just what we need.
		var context = {};
		context.shortName = data.shortName;
		context.symbol = data.symbol;
		context.price = data.ask;

		if(data.quoteType="MUTUALFUND"){
			context.price = data.previousClose
		}

		// call the request to load the chart and pass the data context with it.
		that.LoadChart(context);
	});
};

Site.prototype.SubmitForm = function(){
	this.symbol = $("#symbol").val();
	this.GetQuote();
}

Site.prototype.LoadChart = function(quote){

	var that = this;
	$.ajax({
		url: "/history?symbol=" + that.symbol,
		method: "GET",
		cache: false
	}).done(function(data) {
		console.log('Média Movel Simples (10)', that.simpleMovingAverage(JSON.parse(data).Close, 10, true));
		console.log('Média Movel Simples (20)', that.simpleMovingAverage(JSON.parse(data).Close, 20, true));
		console.log('Média Movel Simples (30)', that.simpleMovingAverage(JSON.parse(data).Close, 30, true));
		console.log('Média Movel Simples (40)', that.simpleMovingAverage(JSON.parse(data).Close, 40, true));
		console.log('Média Movel Simples (50)', that.simpleMovingAverage(JSON.parse(data).Close, 50, true));
		console.log('Média Movel Simples (100)', that.simpleMovingAverage(JSON.parse(data).Close, 100, true));
		console.log('Média Movel Simples (200)', that.simpleMovingAverage(JSON.parse(data).Close, 200, true));
		that.RenderChart(JSON.parse(data), quote);
	});
};

Site.prototype.RenderChart = function(data, quote){
	var priceData = [];
	var volumeData = [];

	var title = quote.shortName  + " (" + quote.symbol + ") - " + numeral(quote.price).format('$0,0.00');


	// Close and Volume data
	for(var i in data.Close){
		var volume = data.Volume[i];
		var close = data.Close[i];

		var dt = parseInt(i);

		if(close != null){
			priceData.push([dt, close]);
		}

		if(volume != null){
			volumeData.push([dt, volume])
		}

	}

	console.log(volumeData);

	Highcharts.stockChart('chart_container', {
		
		yAxis: [{
            labels: {
                align: 'left'
            },
            height: '80%',
            resize: {
                enabled: true
            }
        }, {
            labels: {
                align: 'left'
            },
            top: '80%',
            height: '20%',
            offset: 0
        }],

		rangeSelector: {
			selected: 1
		},
	  
		title: {
			text: title
		},
	  
		series: [{
			name: quote.shortName,
			data: priceData,
			tooltip: {
			  valueDecimals: 2
			}
		},{
			type: 'column',
			id: quote.shortName + '-volume',
			name: quote.shortName + ' Volume',
			data: volumeData,
			yAxis: 1
		}],

		rangeSelector: {
            buttons: [{
                type: 'day',
                count: 1,
                text: '1d'
            },{
                type: 'day',
                count: 3,
                text: '3d'
            },{
                type: 'day',
                count: 7,
                text: '7d'
            },{
                type: 'day',
                count: 15,
                text: '15d'
            },{
                type: 'day',
                count: 30,
                text: '30d'
            },{
                type: 'month',
                count: 3,
                text: '3m'
            }, {
                type: 'day',
                count: 7,
                text: '7D'
            }, {
                type: 'all',
                count: 1,
                text: 'Tudo'
            }],
            selected: 1,
            inputEnabled: false
        },
		
		responsive: {
            rules: [{
                condition: {
                    maxWidth: 800
                },
                chartOptions: {
                    rangeSelector: {
                        inputEnabled: false
                    }
                }
            }]
        }

	});

};

var site = new Site();

$(document).ready(()=>{
	site.Init();
	site.GetQuote();
})
