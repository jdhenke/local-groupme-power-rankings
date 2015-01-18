document.addEventListener("DOMContentLoaded", function() {
    renderTitle();
    renderGraphic();
});

function renderTitle() {
    d3.json("group.json", function(err, data) {
        if (err != null) {
            throw new Exception(err);
        }
        document.querySelector("#title #group-name").innerHTML = data.name;
    });
}

function renderGraphic() {
    var powerRankings = d3.select("#power-rankings");
    d3.json("counts.json", function(err, data) {
        d3.json("power_ranking.json", function(err, rankings) {

            // create lookup from user id to power ranking score

            var lookup = {};
            rankings.forEach(function(ranking) {
                console.log(ranking.nickname, ranking.user_id);
                lookup[ranking.user_id] = ranking.power_ranking;
            })
            data.sort(function(a, b) {
                return lookup[b.user_id] - lookup[a.user_id];
            });

            // setup basic outline for the graphic

            var color = d3.scale.category20();

            var margin = {top: 60, right: 60, bottom: 60, left: 60}
                , width = 780 - margin.left - margin.right
                , height = 500 - margin.top - margin.bottom;

            var x = d3.scale.linear()
                .domain([0, d3.max(data, function(d) { return d.total; })])
                .range([ 0, width - 200 ]);

            var y = d3.scale.linear()
                .domain([0, d3.max(data, function(d) { return d.likes; })])
                .range([ height, 30 ]);

            var chart = powerRankings
                .append('svg:svg')
                .attr('width', 900)
                .attr('height', height + margin.top + margin.bottom)
                .attr('class', 'chart')

            var main = chart.append('g')
                .attr('transform',
                      'translate(' + margin.left + ',' + margin.top + ')')
                .attr('width', width)
                .attr('height', height)
                .attr('class', 'main')


            // draw the axes

            var xAxis = d3.svg.axis()
                .scale(x)
                .orient('bottom');

            main.append('g')
                .attr('transform', 'translate(0,' + height + ')')
                .attr('class', 'main axis date')
                .call(xAxis)
                .append("text")
                .attr("class", "label")
                .attr("x", x.range()[1])
                .attr("y", -6)
                .style("text-anchor", "end")
                .text("Total Messages");

            var yAxis = d3.svg.axis()
                .scale(y)
                .orient('left');

            main.append('g')
                .attr('transform', 'translate(0,0)')
                .attr('class', 'main axis date')
                .call(yAxis)
                .append("text")
                .attr("class", "label")
                .attr("transform", "rotate(-90)")
                .attr("y", 6)
                .attr("x", -30)
                .attr("dy", ".71em")
                .style("text-anchor", "end")
                .text("Total Likes");

            // render the scatter plot

            var g = main.append("svg:g");

            var dots = g.selectAll("scatter-dots")
                .data(data)
                .enter().append("svg:circle")
                .attr("cx", function (d,i) { return x(d.total); } )
                .attr("cy", function (d) { return y(d.likes); } )
                .style("fill", function(d, i) {return color(i)})

            var dotScale = d3.scale.linear()
                .domain(d3.extent(rankings, function(d) { return d.power_ranking; }))
                .range([5,25]);

            dots.attr("r", function(d) {
                return dotScale(lookup[d.user_id]);
            });

            // draw the power rankings

            var barScale = d3.scale.linear()
                .domain(dotScale.domain())
                .range([5, 50]);

            var legend = g.selectAll(".legend")
                .data(data)
                .enter().append("g")
                .attr("class", "legend")
                .attr("transform", function(d, i) { return "translate(0," + (15 + i * 20) + ")"; });

            g.append("text")
                .text("Power Rankings")
                .attr("x", width)
                .attr("text-anchor", "middle")
                .style("font-size", 15)
                .style("font-family", "Trebuchet MS")

            g.append("text")
                .text("Messages vs. Likes")
                .attr("x", 250)
                .attr("text-anchor", "middle")
                .style("font-size", 15)
                .style("font-family", "Trebuchet MS")

            legend.append("rect")
                .attr("x", width - 120)
                .attr("width", function(d) { return 2 * barScale(lookup[d.user_id]); })
                .attr("height", 18)
                .style("fill", function(_, i) {return color(i); });

            legend.append("text")
                .attr("x", width - 125)
                .attr("y", 15)
                .style("text-anchor", "end")
                .text(function(_, i) { return (i + 1) + "."; })

            legend.append("text")
                .attr("x", width - 118)
                .attr("y", 13)
                .text(function(d) { return (100 * lookup[d.user_id]).toFixed(3)});

            legend.append("text")
                .attr("x", width)
                .attr("y", 9)
                .attr("dy", ".35em")
                .style("text-anchor", "start")
                .text(function(d, i) { return d.nickname;});

            // setup mouseover functionality

            function mouseover(_, i) {
                function dim(_, i2) {
                    if (i == i2) {
                        return 1;
                    } else {
                        return 0.15;
                    }
                }
                [dots, legend].forEach(function(viz) {
                    viz.transition().duration(250).style("opacity", dim);
                });

                var x, y, r, name;
                dots.each(function(d, i2) {
                    if (i2 == i) {
                        var sel = d3.select(this);
                        x = parseFloat(sel.attr("cx"));
                        y = parseFloat(sel.attr("cy"));
                        r = parseFloat(sel.attr("r"));
                        name = d.nickname;
                    }
                });
            }

            function mouseout() {
                [dots, legend].forEach(function(viz) {
                    viz.transition().duration(250).style("opacity", 1);
                });
            }

            [dots, legend].forEach(function(viz) {
                viz.on("mouseover", mouseover);
                viz.on("mouseout", mouseout);
            });

        });
    });
}
