import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PlusCircle, Plus } from "lucide-react";
import { Resource } from "@/lib/types";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { ComboboxDemo } from "./Combobox";

type ViewmoreDialogProps = {
	isOpen: boolean;
	onOpenChange: (isOpen: boolean) => void;
	newResource: Resource;
	setNewResource: (resource: Resource) => void;
	addResource: () => void;
};

export function ViewmoreDialog({
	isOpen,
	onOpenChange,
	newResource,
	setNewResource,
	addResource,
}: ViewmoreDialogProps) {
	return (
		<Dialog open={isOpen} onOpenChange={onOpenChange}>
			<DialogTrigger asChild>
				<Button
					variant="link"
					size="sm"
					className="text-sm font-bold text-[#6766FC]"
				>
					View More
				</Button>
			</DialogTrigger>

			<DialogContent className="sm:max-w-[700px] md:max-w-[800px] lg:max-w-[1500px] min-h-[800px] mx-0">
				<DialogTitle className="text-4xl font-bold">
					View More
				</DialogTitle>

				<div className="flex border gap-40">
					<div className="border border-gray-300 p-4 rounded-lg">
						<label className="text-4xl font-bold block mb-4">
							Agent Evaluation Process
						</label>
						<div className="flex flex-col space-y-2">
							{[...Array(5)].map((_, index) => (
								<div
									key={index}
									className="flex items-center space-x-2"
								>
									<span className="text-green-500 text-xl">
										✔️
									</span>
									<span className="text-gray-700">
										Loading
									</span>
								</div>
							))}
						</div>
					</div>
					<div className="border border-gray-300 p-4 rounded-lg flex flex-col items-center">
						<label className="text-4xl font-bold block mb-4 text-center">
							Grade Evaluation Selection
						</label>
						<Popover>
							<ComboboxDemo />
						</Popover>
					</div>
				</div>
				<Button
					onClick={addResource}
					className="w-full bg-[#6766FC] text-white"
					disabled={
						!newResource.url ||
						!newResource.title ||
						!newResource.description
					}
				>
					<Plus className="w-4 h-4 mr-2" /> Submit Response
				</Button>
			</DialogContent>
		</Dialog>
	);
}
