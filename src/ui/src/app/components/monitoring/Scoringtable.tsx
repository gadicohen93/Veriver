import React from "react";

const ScoringTable: React.FC = () => {
	const riskLevels = [
		{
			level: "Low Risk",
			scores: "1 - 4",
			description:
				"No Misinformation Detected to Moderate Misinformation",
		},
		{
			level: "Needs Attention",
			scores: "5 - 10",
			description: "Significant to Egregious Misinformation",
		},
	];

	return (
		<div className="overflow-x-auto">
			<table className="min-w-full border-collapse border border-gray-200">
				<thead>
					<tr>
						<th className="border border-gray-300 p-2">
							Risk Level
						</th>
						<th className="border border-gray-300 p-2">
							Score Range
						</th>
						<th className="border border-gray-300 p-2">
							Description
						</th>
					</tr>
				</thead>
				<tbody>
					{riskLevels.map((item) => (
						<tr key={item.level}>
							<td className="border border-gray-300 p-2 text-center">
								{item.level}
							</td>
							<td className="border border-gray-300 p-2 text-center">
								{item.scores}
							</td>
							<td className="border border-gray-300 p-2">
								{item.description}
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
};

export default ScoringTable;
