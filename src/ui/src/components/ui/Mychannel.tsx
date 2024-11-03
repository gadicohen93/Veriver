import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Table,
	TableBody,
	TableCaption,
	TableCell,
	TableFooter,
	TableHead,
	TableHeader,
	TableRow,
} from "./table";

const ChannelButtons: React.FC = () => {
	const [selectedChannel, setSelectedChannel] = useState("channel1");

	const channels = [
		{ id: "channel1", label: "Channel 1" },
		{ id: "channel2", label: "Channel 2" },
		{ id: "channel3", label: "Channel 3" },
	];

	const messagesarray = [
		{
			tgmessage: "Message 1",
			agentscore: "3",
			agentsummary: "Pull in Agent Summary",
			AgentAnalysis: "Add View More Button",
		},
		{
			tgmessage: "Message 2",
			agentscore: "4",
			agentsummary: "Pull in Agent Summary",
			AgentAnalysis: "Add View More Button",
		},
		{
			tgmessage: "Message 3",
			agentscore: "5",
			agentsummary: "Pull in Agent Summary",
			AgentAnalysis: "Add View More Button",
		},
		{
			tgmessage: "Message 4",
			agentscore: "10",
			agentsummary: "Pull in Agent Summary",
			AgentAnalysis: "Add View More Button",
		},
		{
			tgmessage: "Message 5",
			agentscore: "8",
			agentsummary: "Pull in Agent Summary",
			AgentAnalysis: "Add View More Button",
		},
		{
			tgmessage: "Message 6",
			agentscore: "7",
			agentsummary: "Pull in Agent Summary",
			AgentAnalysis: "Add View More Button",
		},
		{
			tgmessage: "Message 7",
			agentscore: "5",
			agentsummary: "Pull in Agent Summary",
			AgentAnalysis: "Add View More Button",
		},
	];

	return (
		<div className="container">
			<div className="flex justify-around bg-gray-200 p-4 rounded-lg shadow-md">
				{channels.map((channel) => (
					<Button
						key={channel.id}
						className={`flex-1 p-3 mx-1 text-white rounded-lg transition-all ${
							selectedChannel === channel.id
								? "bg-blue-500"
								: "bg-gray-400"
						}`}
						onClick={() => setSelectedChannel(channel.id)}
					>
						{channel.label}
					</Button>
				))}
			</div>
			<Table>
				<TableHeader>
					<TableRow>
						<TableHead className="w-[100px]">Message</TableHead>
						<TableHead>Score</TableHead>
						<TableHead>Summary</TableHead>
						<TableHead>Agent Analysis</TableHead>
						<TableHead className="text-right">
							Human Action
						</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{messagesarray.map((tgmessage) => (
						<TableRow key={tgmessage.tgmessage}>
							<TableCell className="font-medium">
								{tgmessage.tgmessage}
							</TableCell>
							<TableCell>{tgmessage.agentscore}</TableCell>
							<TableCell>{tgmessage.agentsummary}</TableCell>
							<TableCell>{tgmessage.AgentAnalysis}</TableCell>
							<TableCell className="text-right">
								<Button
									className={`flex-1 p-3 mx-1 text-white rounded-lg transition-all ${"bg-blue-500 shadow-lg"}`}
								>
									Response to Analysis
								</Button>
							</TableCell>
						</TableRow>
					))}
				</TableBody>
				<Button
					className={` text-white rounded-lg transition-all ${"bg-blue-500 shadow-lg"}`}
				>
					Load More Messages
				</Button>
			</Table>
		</div>
	);
};

export default ChannelButtons;
