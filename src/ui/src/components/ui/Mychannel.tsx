import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { ViewmoreDialog } from "./ViewmoreDialog";
import { useModelSelectorContext } from "@/lib/model-selector-provider";
import { AgentState, Resource } from "@/lib/types";
import {
	useCoAgent,
	useCoAgentStateRender,
	useCopilotAction,
} from "@copilotkit/react-core";
import { Progress } from "../Progress";

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
	const { model } = useModelSelectorContext();
	const { state, setState } = useCoAgent<AgentState>({
		name: "research_agent",
		initialState: {
			model,
		},
	});

	useCoAgentStateRender({
		name: "research_agent",
		render: ({ state, nodeName, status }) => {
			if (!state.logs || state.logs.length === 0) {
				return null;
			}
			return <Progress logs={state.logs} />;
		},
	});

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

	const resources: Resource[] = state.resources || [];
	const setResources = (resources: Resource[]) => {
		setState({ ...state, resources });
	};

	// const [resources, setResources] = useState<Resource[]>(dummyResources);
	const [newResource, setNewResource] = useState<Resource>({
		url: "",
		title: "",
		description: "",
	});
	const [isAddResourceOpen, setIsAddResourceOpen] = useState(false);

	const addResource = () => {
		if (newResource.url) {
			setResources([...resources, { ...newResource }]);
			setNewResource({ url: "", title: "", description: "" });
			setIsAddResourceOpen(false);
		}
	};

	const removeResource = (url: string) => {
		setResources(
			resources.filter((resource: Resource) => resource.url !== url)
		);
	};

	const [editResource, setEditResource] = useState<Resource | null>(null);
	const [originalUrl, setOriginalUrl] = useState<string | null>(null);
	const [isEditResourceOpen, setIsEditResourceOpen] = useState(false);

	const handleCardClick = (resource: Resource) => {
		setEditResource({ ...resource }); // Ensure a new object is created
		setOriginalUrl(resource.url); // Store the original URL
		setIsEditResourceOpen(true);
	};

	const updateResource = () => {
		if (editResource && originalUrl) {
			setResources(
				resources.map((resource) =>
					resource.url === originalUrl
						? { ...editResource }
						: resource
				)
			);
			setEditResource(null);
			setOriginalUrl(null);
			setIsEditResourceOpen(false);
		}
	};

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
						<TableHead>Human Action</TableHead>
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
							<TableCell>
								<ViewmoreDialog
									isOpen={isAddResourceOpen}
									onOpenChange={setIsAddResourceOpen}
									newResource={newResource}
									setNewResource={setNewResource}
									addResource={addResource}
								/>
							</TableCell>
							<TableCell>
								{/* <Button
									className={`flex-1 p-3 mx-1 text-white rounded-lg transition-all ${"bg-blue-500 shadow-lg"}`}
								>
									Response to Analysis
								</Button> */}
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
