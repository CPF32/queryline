import { useMemo } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import StatCard from "@/components/StatCard";
import { useTheme } from "@/theme/ThemeProvider";
import type { ChartSpec, QueryResult } from "@/types/contracts";
import {
  chartTooltipStyle,
  getChartTheme,
} from "@/utils/chartTheme";
import {
  formatCellValue,
  queryResultToRecords,
  toNumeric,
} from "@/utils/queryData";

export interface ChartRendererProps {
  chartSpec: ChartSpec;
  queryResult: QueryResult;
}

export default function ChartRenderer({
  chartSpec,
  queryResult,
}: ChartRendererProps) {
  const { theme } = useTheme();
  const chartTheme = useMemo(() => getChartTheme(), [theme]);

  const chartData = useMemo(
    () => prepareChartData(chartSpec, queryResult),
    [chartSpec, queryResult],
  );

  if (chartSpec.chart_type === "table_only") {
    return null;
  }

  if (chartSpec.chart_type === "stat_card") {
    const field = chartSpec.y_fields[0];
    const rawValue = field ? chartData.records[0]?.[field] : undefined;
    return (
      <StatCard
        title={chartSpec.title}
        value={formatCellValue(rawValue)}
      />
    );
  }

  return (
    <div className="chart-renderer">
      <h3 className="chart-renderer__title">{chartSpec.title}</h3>
      <div className="chart-renderer__canvas">
        <ResponsiveContainer width="100%" height="100%">
          {renderChart(chartSpec, chartData.records, chartData.seriesKeys, chartTheme)}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

interface PreparedChartData {
  records: Record<string, unknown>[];
  seriesKeys: string[];
}

function prepareChartData(
  chartSpec: ChartSpec,
  queryResult: QueryResult,
): PreparedChartData {
  const baseRecords = queryResultToRecords(queryResult);

  if (!chartSpec.series_field || !chartSpec.x_field) {
    return {
      records: baseRecords,
      seriesKeys: chartSpec.y_fields,
    };
  }

  const seriesValues = Array.from(
    new Set(
      baseRecords
        .map((record) => record[chartSpec.series_field!])
        .filter((value) => value !== null && value !== undefined)
        .map(String),
    ),
  );

  const xValues = Array.from(
    new Set(baseRecords.map((record) => String(record[chartSpec.x_field!]))),
  );

  const pivoted = xValues.map((xValue) => {
    const row: Record<string, unknown> = { [chartSpec.x_field!]: xValue };
    seriesValues.forEach((seriesValue) => {
      const match = baseRecords.find(
        (record) =>
          String(record[chartSpec.x_field!]) === xValue &&
          String(record[chartSpec.series_field!]) === seriesValue,
      );
      chartSpec.y_fields.forEach((yField) => {
        row[`${seriesValue}__${yField}`] = match?.[yField] ?? null;
      });
    });
    return row;
  });

  return {
    records: pivoted,
    seriesKeys: seriesValues.flatMap((seriesValue) =>
      chartSpec.y_fields.map((yField) => `${seriesValue}__${yField}`),
    ),
  };
}

function axisTick(theme: ReturnType<typeof getChartTheme>) {
  return { fontSize: 12, fill: theme.tick };
}

function renderChart(
  chartSpec: ChartSpec,
  records: Record<string, unknown>[],
  seriesKeys: string[],
  theme: ReturnType<typeof getChartTheme>,
) {
  const xField = chartSpec.x_field ?? "x";
  const tooltipStyle = chartTooltipStyle(theme);
  const tick = axisTick(theme);

  switch (chartSpec.chart_type) {
    case "bar":
      return (
        <BarChart data={records}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          <XAxis dataKey={xField} tick={tick} stroke={theme.grid} />
          <YAxis tick={tick} stroke={theme.grid} />
          <Tooltip contentStyle={tooltipStyle} />
          {seriesKeys.length > 1 && <Legend />}
          {seriesKeys.map((key, index) => (
            <Bar
              key={key}
              dataKey={key}
              fill={theme.colors[index % theme.colors.length]}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      );

    case "line":
      return (
        <LineChart data={records}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          <XAxis dataKey={xField} tick={tick} stroke={theme.grid} />
          <YAxis tick={tick} stroke={theme.grid} />
          <Tooltip contentStyle={tooltipStyle} />
          {seriesKeys.length > 1 && <Legend />}
          {seriesKeys.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={theme.colors[index % theme.colors.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      );

    case "area":
      return (
        <AreaChart data={records}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          <XAxis dataKey={xField} tick={tick} stroke={theme.grid} />
          <YAxis tick={tick} stroke={theme.grid} />
          <Tooltip contentStyle={tooltipStyle} />
          {seriesKeys.length > 1 && <Legend />}
          {seriesKeys.map((key, index) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stroke={theme.colors[index % theme.colors.length]}
              fill={theme.colors[index % theme.colors.length]}
              fillOpacity={0.2}
            />
          ))}
        </AreaChart>
      );

    case "scatter": {
      const yField = chartSpec.y_fields[0];
      const scatterData = records
        .map((record) => ({
          x: toNumeric(record[xField]),
          y: yField ? toNumeric(record[yField]) : null,
        }))
        .filter((point) => point.x !== null && point.y !== null);

      return (
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          <XAxis type="number" dataKey="x" name={xField} tick={tick} stroke={theme.grid} />
          <YAxis type="number" dataKey="y" name={yField} tick={tick} stroke={theme.grid} />
          <ZAxis range={[60, 60]} />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={tooltipStyle} />
          <Scatter data={scatterData} fill={theme.colors[0]} />
        </ScatterChart>
      );
    }

    case "pie": {
      const valueField = chartSpec.y_fields[0];
      const pieData = records.map((record) => ({
        name: String(record[xField] ?? ""),
        value: valueField ? toNumeric(record[valueField]) ?? 0 : 0,
      }));

      return (
        <PieChart>
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <Pie
            data={pieData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius="70%"
            label={{ fill: theme.tick, fontSize: 12 }}
          >
            {pieData.map((_, index) => (
              <Cell
                key={`slice-${index}`}
                fill={theme.colors[index % theme.colors.length]}
              />
            ))}
          </Pie>
        </PieChart>
      );
    }

    default:
      return <div />;
  }
}
