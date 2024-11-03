"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
	useCoAgent,
	useCoAgentStateRender,
	useCopilotAction,
} from "@copilotkit/react-core";
import { Progress } from "./Progress";
import { EditResourceDialog } from "./EditResourceDialog";
import { AddResourceDialog } from "./Addtelegramchannel";
import { Resources } from "./Resources";
import { AgentState, Resource } from "@/lib/types";
import { useModelSelectorContext } from "@/lib/model-selector-provider";
import BasicDropdown from "./ui/Mychannel";

export function ResearchCanvas() {
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

	useCopilotAction({
		name: "DeleteResources",
		disabled: true,
		parameters: [
			{
				name: "urls",
				type: "string[]",
			},
		],
		renderAndWait: ({ args, status, handler }) => {
			return (
				<div className="">
					<div className="font-bold text-base mb-2">
						Delete these resources?
					</div>
					<Resources
						resources={resources.filter((resource) =>
							(args.urls || []).includes(resource.url)
						)}
						customWidth={200}
					/>
					{status === "executing" && (
						<div className="mt-4 flex justify-start space-x-2">
							<button
								onClick={() => handler("NO")}
								className="px-4 py-2 text-[#6766FC] border border-[#6766FC] rounded text-sm font-bold"
							>
								Cancel
							</button>
							<button
								onClick={() => handler("YES")}
								className="px-4 py-2 bg-[#6766FC] text-white rounded text-sm font-bold"
							>
								Delete
							</button>
						</div>
					)}
				</div>
			);
		},
	});

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
		<div className=" bg-[#ffffff]">
			<div>
				<div>
					<div className="flex justify-between items-center mb-4">
						<h2 className="text-lg my-5 font-medium text-primary">
							<AddResourceDialog
								isOpen={isAddResourceOpen}
								onOpenChange={setIsAddResourceOpen}
								newResource={newResource}
								setNewResource={setNewResource}
								addResource={addResource}
							/>
						</h2>

						<EditResourceDialog
							isOpen={isEditResourceOpen}
							onOpenChange={setIsEditResourceOpen}
							editResource={editResource}
							setEditResource={setEditResource}
							updateResource={updateResource}
						/>
					</div>
					{/* {resources.length === 0 && (
						<div className="text-sm text-slate-400">
							Click the button above to add resources.
						</div>
					)} */}

					{resources.length !== 0 && (
						<Resources
							resources={resources}
							handleCardClick={handleCardClick}
							removeResource={removeResource}
						/>
					)}
				</div>

				<div className=" ">
					<h2 className="text-lg ml-5  font-bold mb-3 text-primary underline">
						My Channels
					</h2>

					<BasicDropdown />
					{/* <Textarea
						placeholder="Write your research draft here"
						value={state.report || ""}
						onChange={(e) =>
							setState({ ...state, report: e.target.value })
						}
						rows={10}
						aria-label="Research draft"
						className="bg-background px-6 py-8 border-0 shadow-none rounded-xl text-md font-extralight focus-visible:ring-0 placeholder:text-slate-400"
						style={{ minHeight: "200px" }}
					/> */}
				</div>
			</div>
		</div>
	);
}
