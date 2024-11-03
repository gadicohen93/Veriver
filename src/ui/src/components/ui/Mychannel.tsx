import React, { useState, useEffect, useCallback } from "react";
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
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

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

import { fetchLatestTelegramMessages, fetchTelegramMessages } from "../../api"

const MediaDisplay: React.FC<{ mediaUrls: string[], mediaType: string }> = ({ mediaUrls, mediaType }) => {
	if (!mediaUrls || mediaUrls.length === 0) return null;

	return (
		<div className="flex flex-wrap gap-2">
			{mediaUrls.map((url, index) => {
				if (mediaType.toLowerCase().includes('photo')) {
					return (
						// eslint-disable-next-line @next/next/no-img-element
						<img 
							key={index}
							src={url} 
							alt="Message media"
							className="max-w-[200px] h-auto rounded-lg cursor-pointer hover:opacity-90"
							onClick={() => window.open(url, '_blank')}
						/>
					);
				} else if (mediaType.toLowerCase().includes('video')) {
					return (
						<video 
							key={index}
							controls
							className="max-w-[200px] h-auto rounded-lg"
						>
							<source src={url} type="video/mp4" />
							Your browser does not support the video tag.
						</video>
					);
				} else {
					return (
						<a 
							key={index}
							href={url} 
							target="_blank" 
							rel="noopener noreferrer"
							className="text-blue-500 hover:underline"
						>
							View Media
						</a>
					);
				}
			})}
		</div>
	);
};

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

	const [messages, setMessages] = useState<any[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

	const [latestMessageId, setLatestMessageId] = useState<number | null>(null);
	const POLLING_INTERVAL = 5000; // 5 seconds

	const loadMessages = useCallback(async (isInitial: boolean = false) => {
		setIsLoading(isInitial); // Only show loading state on initial load
		try {
			const response = await fetchLatestTelegramMessages();
			if (isInitial) {
				setMessages(response.messages);
				setLatestMessageId(response.messages[0]?.message_id ?? null);
			} else {
				// For subsequent polls, merge new messages without duplicates
				const newMessages = response.messages.filter(
					(newMsg: any) => newMsg.message_id > (latestMessageId ?? 0)
				);
				
				if (newMessages.length > 0) {
					setMessages(prevMessages => {
						const merged = [...newMessages, ...prevMessages];
						// Keep sorted by date if that's the current sort direction
						if (sortDirection === 'desc') {
							merged.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
						} else {
							merged.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
						}
						return merged;
					});
					setLatestMessageId(newMessages[0].message_id);
				}
			}
		} catch (err) {
			setError(err instanceof Error ? err.message : 'Failed to load messages');
		} finally {
			setIsLoading(false);
		}
	}, [latestMessageId, sortDirection]);

	useEffect(() => {
		loadMessages(true);
	}, [loadMessages, selectedChannel]);

	useEffect(() => {
		const pollInterval = setInterval(() => {
			loadMessages(false);
		}, POLLING_INTERVAL);

		// Cleanup on unmount
		return () => clearInterval(pollInterval);
	}, [selectedChannel, latestMessageId, sortDirection, loadMessages]);

	const [newResource, setNewResource] = useState<Resource>({
		url: "",
		title: "",
		description: "",
	});
	const [isAddResourceOpen, setIsAddResourceOpen] = useState(false);

	const addResource = () => {
		if (newResource.url) {
			setState({ ...state, resources: [...state.resources, { ...newResource }] });
			setNewResource({ url: "", title: "", description: "" });
			setIsAddResourceOpen(false);
		}
	};

	const removeResource = (url: string) => {
		setState({ ...state, resources: state.resources.filter((resource: Resource) => resource.url !== url) });
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
			setState({ ...state, resources: state.resources.map((resource) =>
				resource.url === originalUrl
					? { ...editResource }
					: resource
			) });
			setEditResource(null);
			setOriginalUrl(null);
			setIsEditResourceOpen(false);
		}
	};

	const handleDateSort = () => {
		const sortedMessages = [...messages].sort((a, b) => {
			const dateA = new Date(a.date).getTime();
			const dateB = new Date(b.date).getTime();
			return sortDirection === 'asc' ? dateA - dateB : dateB - dateA;
		});
		setMessages(sortedMessages);
		setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
	};

	return (
		<Card className="w-full">
			<CardContent className="p-6">
				<Tabs 
					defaultValue={selectedChannel} 
					onValueChange={setSelectedChannel}
					className="w-full mb-6"
				>
					<TabsList className="w-full">
						{channels.map((channel) => (
							<TabsTrigger
								key={channel.id}
								value={channel.id}
								className="flex-1"
							>
								{channel.label}
							</TabsTrigger>
						))}
					</TabsList>
				</Tabs>

				{isLoading ? (
					<div className="space-y-3">
						<Skeleton className="h-20 w-full" />
						<Skeleton className="h-20 w-full" />
						<Skeleton className="h-20 w-full" />
					</div>
				) : error ? (
					<div className="flex items-center justify-center p-6 text-red-500">
						<span className="text-sm font-medium">{error}</span>
					</div>
				) : (
					<ScrollArea className="h-[600px] rounded-md border">
						<Table>
							<TableHeader>
								<TableRow>
									<TableHead className="w-[50%]">Message</TableHead>
									<TableHead className="w-[15%] text-right">Views</TableHead>
									<TableHead className="w-[15%] text-right">Forwards</TableHead>
									<TableHead 
										className="w-[20%] cursor-pointer hover:text-gray-700"
										onClick={handleDateSort}
									>
										Date {sortDirection === 'asc' ? '↑' : '↓'}
									</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{messages.map((message) => (
									<TableRow key={message.message_id}>
										<TableCell className="font-medium">
											<div className="space-y-2">
												<p className="text-sm leading-relaxed">{message.text}</p>
												{message.has_media && (
													<MediaDisplay 
														mediaUrls={message.media_urls || []} 
														mediaType={message.media_type || ''}
													/>
												)}
											</div>
										</TableCell>
										<TableCell className="text-right">{message.views || 0}</TableCell>
										<TableCell className="text-right">{message.forwards || 0}</TableCell>
										<TableCell>{new Date(message.date).toLocaleString()}</TableCell>
									</TableRow>
								))}
							</TableBody>
						</Table>
					</ScrollArea>
				)}
			</CardContent>
		</Card>
	);
};

export default ChannelButtons;
